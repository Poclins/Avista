"""Clasificador basado en reglas (camino secundario/local del Módulo E).

Implementa el puerto :class:`~app.providers.classifier.base.Classifier` sin
dependencias de red: estima el ``nivel_estimado`` (1–9) y entre 1 y 5 dominios a
partir del texto de una observación usando coincidencias léxicas contra un
**catálogo de manifestaciones** del dataset E-1, y vincula entre 1 y 10
manifestaciones cuyo ``nivel`` sea igual al ``nivel_estimado`` y cuyo
``dominio`` pertenezca a los dominios estimados (Requirements 3.1, 3.2).

Es el camino **secundario** (local/CI) tras la misma interfaz que el adaptador
LLM primario; ambos son intercambiables (LSP) y se seleccionan por ``USE_MOCKS``.

Aislamiento (tarea 6.1): solo depende del **dominio del Módulo A**
(``Manifestacion``, ``Dominio``, ``ClasificacionPropuesta``). El catálogo de
manifestaciones se **inyecta** como una lista de modelos de dominio; no importa
la implementación concreta de ningún repositorio hermano (p. ej. ``RelationalRepo``).

Baja confianza / texto vacío (Requirement 3.5): si el texto está vacío o la
confianza estimada queda por debajo de ``umbral_confianza``, devuelve una
``ClasificacionPropuesta`` marcada como **pendiente de clasificación manual**,
conservando el texto sin descartarlo.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable

from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import NIVEL_MAX, NIVEL_MIN, Dominio, Manifestacion
from app.providers.classifier.base import Classifier

# Palabras vacías del español que no aportan señal de clasificación.
_STOPWORDS: frozenset[str] = frozenset(
    """
    a al algo algun alguna algunas alguno algunos ante antes como con contra cual
    cuando de del desde donde dos el ella ellas ellos en entre era erais eran eras
    eres es esa esas ese eso esos esta estas este esto estos ha hace hacia han hay
    la las le les lo los mas me mi mis mucho muy nada ni no nos o os otra otras otro
    otros para pero poco por porque que quien se segun ser si sin sobre su sus tan
    te ti tu tus un una unas uno unos y ya
    """.split()
)

# Pistas léxicas por dominio: lemas/raíces frecuentes en las observaciones E-1.
# Se usan como refuerzo cuando el texto no coincide directamente con el catálogo.
_PISTAS_DOMINIO: dict[Dominio, frozenset[str]] = {
    Dominio.cognitivo: frozenset(
        "clasific color forma encaj rompecabez resuelv cuent numer compar atencion "
        "memoria causa secuenc razon problema patron agrup".split()
    ),
    Dominio.lenguaje_comunicacion: frozenset(
        "nombr palabra habla dice cuenta pregunt instruccion frase relato narr "
        "comunic conversa vocabulario escuch responde".split()
    ),
    Dominio.motor_fino: frozenset(
        "pinza lapiz traz dibuj recort pega abotona enhebr pequeñ dedos mano "
        "garaba tijera modela".split()
    ),
    Dominio.motor_grueso: frozenset(
        "corre salta camin equilibrio pelota lanza trepa sube baja obstaculo "
        "desplaza gatea brinca".split()
    ),
    Dominio.socioemocional: frozenset(
        "comparte emocion amigo turno espera consuela saluda juega ayuda frustr "
        "enoj content triste autonom independ".split()
    ),
}


def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, para comparación robusta en español."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokens(texto: str) -> list[str]:
    """Tokeniza en palabras alfabéticas (incluye ñ), descartando stopwords."""
    normal = _normalizar(texto)
    palabras = re.findall(r"[a-zñ]+", normal)
    return [p for p in palabras if len(p) >= 3 and p not in _STOPWORDS]


class RuleBasedClassifier(Classifier):
    """Clasificador léxico sobre un catálogo de manifestaciones del dataset E-1.

    Args:
        catalogo: manifestaciones del dominio (Módulo A) sobre las que puntuar y
            vincular. Puede inyectarse desde un seed/fixture o un repositorio
            (vía su interfaz) sin acoplar este adaptador a una implementación.
        umbral_confianza: por debajo de este valor la clasificación se marca como
            pendiente de clasificación manual (Requirement 3.5). Rango 0.0–1.0.
        max_dominios: tope de dominios estimados (contrato: 1–5).
        max_manifestaciones: tope de manifestaciones vinculadas (contrato: 1–10).
    """

    def __init__(
        self,
        catalogo: Iterable[Manifestacion],
        *,
        umbral_confianza: float = 0.15,
        max_dominios: int = 5,
        max_manifestaciones: int = 10,
    ) -> None:
        self._catalogo: list[Manifestacion] = list(catalogo)
        self._umbral_confianza = umbral_confianza
        self._max_dominios = max(1, min(5, max_dominios))
        self._max_manifestaciones = max(1, min(10, max_manifestaciones))
        # Tokens precomputados por manifestación para puntuar coincidencias.
        self._tokens_catalogo: list[frozenset[str]] = [
            frozenset(_tokens(m.texto_observable)) for m in self._catalogo
        ]

    # -- API del puerto ----------------------------------------------------
    def classify(self, texto: str) -> ClasificacionPropuesta:
        """Clasifica el texto; marca pendiente si está vacío o la confianza es baja."""
        if texto is None or not texto.strip():
            # Texto vacío → pendiente de clasificación manual (Requirement 3.5).
            return self._pendiente()

        tokens = set(_tokens(texto))
        if not tokens or not self._catalogo:
            return self._pendiente()

        # 1) Puntuar cada manifestación por solapamiento léxico con el texto.
        puntajes: list[float] = []
        for m, toks in zip(self._catalogo, self._tokens_catalogo):
            solapamiento = len(tokens & toks)
            # Refuerzo con pistas de dominio (señal débil cuando no hay match directo).
            pistas = _PISTAS_DOMINIO.get(m.dominio, frozenset())
            refuerzo = sum(
                1 for t in tokens if any(t.startswith(p) for p in pistas)
            )
            puntajes.append(float(solapamiento) * 2.0 + float(refuerzo) * 0.5)

        mejor = max(puntajes) if puntajes else 0.0
        if mejor <= 0.0:
            # Ninguna señal: no inventamos una clasificación (Requirement 3.5).
            return self._pendiente()

        # 2) Estimar el nivel: media ponderada de los niveles de las
        #    manifestaciones con mejor puntaje (voto ponderado por score).
        nivel_estimado = self._estimar_nivel(puntajes)

        # 3) Estimar los dominios (1–5) a partir del puntaje acumulado por dominio.
        dominios = self._estimar_dominios(puntajes)

        # 4) Vincular 1–10 manifestaciones con nivel == nivel_estimado y
        #    dominio ∈ dominios estimados (Requirement 3.2).
        manifestaciones = self._vincular(nivel_estimado, dominios, puntajes)

        # Si el vínculo quedó vacío (p. ej. el catálogo no cubre ese nivel/dominio),
        # relajamos a dominio ∈ dominios sin exigir el nivel exacto como respaldo.
        if not manifestaciones:
            manifestaciones = self._vincular(None, dominios, puntajes)
        if not manifestaciones:
            return self._pendiente()

        confianza = self._confianza(puntajes, tokens)
        if confianza < self._umbral_confianza:
            return self._pendiente(confianza=confianza)

        return ClasificacionPropuesta(
            nivel_estimado=nivel_estimado,
            dominios=dominios,
            manifestaciones=manifestaciones,
            confianza=round(confianza, 2),
            pendiente_clasificacion_manual=False,
        )

    # -- Internos ----------------------------------------------------------
    def _estimar_nivel(self, puntajes: list[float]) -> int:
        """Nivel más votado, ponderado por el puntaje de cada manifestación."""
        votos: Counter[int] = Counter()
        for m, score in zip(self._catalogo, puntajes):
            if score > 0.0:
                votos[m.nivel] += score
        if not votos:
            return NIVEL_MIN
        nivel = max(votos, key=lambda n: votos[n])
        return max(NIVEL_MIN, min(NIVEL_MAX, nivel))

    def _estimar_dominios(self, puntajes: list[float]) -> list[Dominio]:
        """Dominios con mayor puntaje acumulado (1–5), orden descendente."""
        acum: Counter[Dominio] = Counter()
        for m, score in zip(self._catalogo, puntajes):
            if score > 0.0:
                acum[m.dominio] += score
        if not acum:
            return []
        ordenados = [d for d, _ in acum.most_common(self._max_dominios)]
        return ordenados

    def _vincular(
        self,
        nivel: int | None,
        dominios: list[Dominio],
        puntajes: list[float],
    ) -> list[str]:
        """Selecciona hasta 10 manifestaciones coherentes, por puntaje descendente.

        Coherencia (Requirement 3.2): ``dominio ∈ dominios`` y, cuando ``nivel``
        no es ``None``, ``manifestacion.nivel == nivel``.
        """
        dominios_set = set(dominios)
        candidatas: list[tuple[float, str]] = []
        for m, score in zip(self._catalogo, puntajes):
            if m.dominio not in dominios_set:
                continue
            if nivel is not None and m.nivel != nivel:
                continue
            if score <= 0.0:
                continue
            candidatas.append((score, m.id_manifestacion))
        # Mayor puntaje primero; empates estables por id para reproducibilidad.
        candidatas.sort(key=lambda t: (-t[0], t[1]))
        return [id_ for _, id_ in candidatas[: self._max_manifestaciones]]

    def _confianza(self, puntajes: list[float], tokens: set[str]) -> float:
        """Confianza 0–1: concentración de la señal relativa al texto.

        Combina cuántas manifestaciones coincidieron y qué tan fuerte fue la
        mejor coincidencia respecto del tamaño del texto. Es una heurística
        acotada; el objetivo es separar señal clara de ruido para la bandera
        de pendiente (Requirement 3.5), no calibrar una probabilidad real.
        """
        positivos = [p for p in puntajes if p > 0.0]
        if not positivos or not tokens:
            return 0.0
        mejor = max(positivos)
        # Normaliza por el número de tokens del texto (textos cortos y precisos
        # obtienen más confianza que textos largos con una coincidencia aislada).
        densidad = mejor / float(len(tokens) + mejor)
        return max(0.0, min(1.0, densidad))

    def _pendiente(self, *, confianza: float = 0.0) -> ClasificacionPropuesta:
        """Clasificación pendiente de revisión manual (conserva el texto)."""
        return ClasificacionPropuesta(
            nivel_estimado=None,
            dominios=[],
            manifestaciones=[],
            confianza=round(confianza, 2),
            pendiente_clasificacion_manual=True,
        )


__all__ = ["RuleBasedClassifier"]
