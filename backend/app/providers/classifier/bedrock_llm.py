"""Clasificador basado en LLM (camino primario del Módulo E).

Implementa el puerto :class:`~app.providers.classifier.base.Classifier` usando un
:class:`~app.providers.llm.base.LlmProvider` (Bedrock/Claude en producción,
mock en local). Pide al modelo que estime el ``nivel_estimado`` (1–9) y entre 1 y
5 dominios del conjunto cerrado, y luego **vincula las manifestaciones de forma
determinista** contra un catálogo del dataset E-1: nunca confía ciegamente en
los identificadores que invente el modelo, sino que selecciona manifestaciones
reales cuyo ``nivel == nivel_estimado`` y ``dominio ∈ dominios`` (Requirements
3.1, 3.2).

Aislamiento (tarea 6.1): este adaptador depende **solo del dominio del Módulo A**
y de la **interfaz** ``LlmProvider``; no importa la implementación concreta de
ningún módulo hermano. Para pruebas en aislamiento se inyecta un ``LlmProvider``
falso (ver tests del módulo).

Baja confianza / fallo (Requirement 3.5): si el texto está vacío, si el LLM
falla o si su salida no permite derivar una clasificación coherente, devuelve una
``ClasificacionPropuesta`` marcada como **pendiente de clasificación manual**,
conservando el texto sin descartarlo.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import NIVEL_MAX, NIVEL_MIN, Dominio, Manifestacion
from app.providers.classifier.base import Classifier
from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider

# Instrucción que fija el conjunto cerrado y el formato de salida JSON.
_PROMPT = (
    "Eres un asistente pedagógico que clasifica observaciones de desarrollo "
    "infantil. A partir del texto de la observación, estima el nivel de "
    "desarrollo (un entero entre 1 y 9) y entre 1 y 5 dominios del conjunto "
    "cerrado: cognitivo, lenguaje_comunicacion, motor_fino, motor_grueso, "
    "socioemocional. Devuelve EXCLUSIVAMENTE un objeto JSON con las claves "
    '"nivel_estimado" (entero 1-9), "dominios" (lista de 1 a 5 dominios del '
    'conjunto cerrado) y "confianza" (número entre 0 y 1). No agregues texto '
    "fuera del JSON."
)


class LlmClassifier(Classifier):
    """Clasificador que delega la estimación al LLM y vincula contra el catálogo.

    Args:
        llm: proveedor LLM (interfaz) que genera la estimación en JSON.
        catalogo: manifestaciones del dominio (Módulo A) para el vínculo
            determinista de 1–10 manifestaciones coherentes.
        umbral_confianza: por debajo de este valor se marca pendiente de
            clasificación manual (Requirement 3.5).
        max_manifestaciones: tope de manifestaciones vinculadas (contrato 1–10).
    """

    def __init__(
        self,
        llm: LlmProvider,
        catalogo: Iterable[Manifestacion],
        *,
        umbral_confianza: float = 0.5,
        max_manifestaciones: int = 10,
    ) -> None:
        self._llm = llm
        self._catalogo: list[Manifestacion] = list(catalogo)
        self._umbral_confianza = umbral_confianza
        self._max_manifestaciones = max(1, min(10, max_manifestaciones))

    def classify(self, texto: str) -> ClasificacionPropuesta:
        """Clasifica el texto; marca pendiente ante texto vacío, fallo o baja confianza."""
        if texto is None or not texto.strip():
            return self._pendiente()

        try:
            salida = self._llm.generate(_PROMPT, texto)
        except LlmError:
            # Fallo del LLM: no se descarta el texto (Requirement 3.5).
            return self._pendiente()

        datos = self._parsear(salida)
        if datos is None:
            return self._pendiente()

        nivel, dominios, confianza = datos
        if nivel is None or not dominios:
            return self._pendiente(confianza=confianza)

        manifestaciones = self._vincular(nivel, dominios)
        if not manifestaciones:
            return self._pendiente(confianza=confianza)

        if confianza < self._umbral_confianza:
            # Conservar la propuesta para que la educadora pueda revisarla;
            # baja confianza no debe borrar nivel, dominios ni vínculos E-1.
            return ClasificacionPropuesta(
                nivel_estimado=nivel,
                dominios=dominios,
                manifestaciones=manifestaciones,
                confianza=round(confianza, 2),
                pendiente_clasificacion_manual=True,
            )

        return ClasificacionPropuesta(
            nivel_estimado=nivel,
            dominios=dominios,
            manifestaciones=manifestaciones,
            confianza=round(confianza, 2),
            pendiente_clasificacion_manual=False,
        )

    # -- Internos ----------------------------------------------------------
    def _parsear(
        self, salida: str
    ) -> tuple[int | None, list[Dominio], float] | None:
        """Extrae ``(nivel, dominios, confianza)`` del JSON del LLM, tolerante a ruido."""
        bloque = self._extraer_json(salida)
        if bloque is None:
            return None
        try:
            obj = json.loads(bloque)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(obj, dict):
            return None

        # Nivel acotado a 1–9; valores fuera de rango o no enteros → None.
        nivel: int | None = None
        bruto_nivel = obj.get("nivel_estimado")
        if isinstance(bruto_nivel, bool):
            bruto_nivel = None
        if isinstance(bruto_nivel, (int, float)):
            n = int(bruto_nivel)
            if NIVEL_MIN <= n <= NIVEL_MAX:
                nivel = n

        # Dominios: solo valores del conjunto cerrado, de-duplicados, máx. 5.
        dominios: list[Dominio] = []
        bruto_dominios = obj.get("dominios", [])
        if isinstance(bruto_dominios, list):
            vistos: set[Dominio] = set()
            for d in bruto_dominios:
                try:
                    dom = Dominio(d)
                except (ValueError, TypeError):
                    continue
                if dom not in vistos:
                    vistos.add(dom)
                    dominios.append(dom)
                if len(dominios) >= 5:
                    break

        # Confianza acotada a 0–1 (si falta o es inválida, 0.0).
        confianza = 0.0
        bruto_conf = obj.get("confianza")
        if isinstance(bruto_conf, (int, float)) and not isinstance(bruto_conf, bool):
            confianza = max(0.0, min(1.0, float(bruto_conf)))

        return nivel, dominios, confianza

    @staticmethod
    def _extraer_json(salida: str) -> str | None:
        """Devuelve el primer objeto ``{...}`` encontrado en el texto, o ``None``."""
        if not salida:
            return None
        match = re.search(r"\{.*\}", salida, re.DOTALL)
        return match.group(0) if match else None

    def _vincular(self, nivel: int, dominios: list[Dominio]) -> list[str]:
        """Vincula hasta 10 manifestaciones con ``nivel`` exacto y dominio ∈ dominios."""
        dominios_set = set(dominios)
        seleccion = [
            m.id_manifestacion
            for m in self._catalogo
            if m.nivel == nivel and m.dominio in dominios_set
        ]
        return seleccion[: self._max_manifestaciones]

    def _pendiente(self, *, confianza: float = 0.0) -> ClasificacionPropuesta:
        """Clasificación pendiente de revisión manual (conserva el texto)."""
        return ClasificacionPropuesta(
            nivel_estimado=None,
            dominios=[],
            manifestaciones=[],
            confianza=round(confianza, 2),
            pendiente_clasificacion_manual=True,
        )


__all__ = ["LlmClassifier"]
