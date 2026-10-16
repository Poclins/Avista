"""Resguardo de datos sensibles — guardia de despersonalización (Transversal).

Este módulo implementa el **control transversal de privacidad** del Requirement
11: antes de que cualquier texto se envíe al ``LlmProvider``, se inspecciona en
busca de **datos directamente identificatorios** (RUT, dirección, datos de
contacto y nombres reales). Si detecta alguno, el envío se **bloquea**, el evento
se **registra** y se levanta una excepción tipada en español
(:class:`DatosSensiblesError`), sin transmitir el dato al LLM
(Requirements 11.1, 11.2, 11.3).

Diseño (SOLID):

- **SRP**: la clase :class:`GuardiaDespersonalizacion` solo decide si un texto
  contiene datos no permitidos; no sabe nada del LLM ni de HTTP.
- **OCP/DIP**: se usa como colaborador de un decorador del puerto
  ``LlmProvider`` (:class:`app.providers.llm.guarded_llm.GuardedLlmProvider`),
  de modo que **todos** los caminos de invocación al LLM (bitácora,
  recomendación, reporte de dirección) quedan protegidos sin duplicar lógica ni
  tocar los servicios.

El sistema trabaja con el dataset E-1 seudonimizado (solo ``id_nino``), por lo
que en operación normal el guardia **no** debería activarse: actúa como red de
seguridad defensiva frente a texto crudo que, por error, arrastre un dato
identificatorio.

Importante sobre falsos positivos: el identificador seudónimo ``id_nino`` (p. ej.
``N-00042``) **no** es un dato sensible; los patrones están afinados para no
confundirlo con un nombre real ni con un RUT.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("jaimes.privacidad")


class DatosSensiblesError(Exception):
    """El contenido destinado al LLM contiene datos no permitidos (11.3).

    Lleva un mensaje en español, apto para exponerse al cliente, que indica que
    el contenido contiene datos no permitidos **sin** incluir el dato detectado
    (no se filtra el valor sensible). Las categorías detectadas se adjuntan en
    :attr:`categorias` para registro/trazabilidad interna.
    """

    def __init__(self, categorias: list[str]) -> None:
        self.categorias = categorias
        super().__init__(
            "El contenido contiene datos no permitidos (información "
            "directamente identificatoria) y no puede enviarse al modelo de "
            "lenguaje. Elimine nombres reales, RUT, direcciones o datos de "
            "contacto y conserve solo el identificador seudónimo del niño/a."
        )


@dataclass(frozen=True)
class Hallazgo:
    """Resultado de inspeccionar un texto: categorías de dato sensible halladas."""

    categorias: tuple[str, ...]

    @property
    def hay_datos_sensibles(self) -> bool:
        return bool(self.categorias)


# ---------------------------------------------------------------------------
# Patrones de detección
# ---------------------------------------------------------------------------
# RUT chileno: 7–8 dígitos + guion + dígito verificador (0–9 o K), con puntos de
# miles opcionales. Ej.: ``12.345.678-5`` o ``12345678-K``. Se exige el guion y
# el dígito verificador para no confundirlo con otros números.
_RUT = re.compile(
    r"\b\d{1,2}\.?\d{3}\.?\d{3}\s*-\s*[\dkK]\b",
)

# Teléfono chileno / número de contacto: +56 opcional, 8–9 dígitos, admite
# separadores. Ej.: ``+56 9 1234 5678``, ``912345678``, ``22 234 5678``.
_TELEFONO = re.compile(
    r"(?<!\d)(?:\+?56\s*)?(?:9\s*\d{4}\s*\d{4}|\d{2}\s*\d{3}\s*\d{4})(?!\d)",
)

# Correo electrónico (dato de contacto).
_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
)

# Dirección: palabra clave de vía + número. Ej.: ``Av. Las Flores 123``,
# ``Pasaje Los Olivos 45``, ``calle Larga 1200``. Se admiten puntos intermedios
# (p. ej. la abreviatura ``Av.``) entre la vía y el número.
_DIRECCION = re.compile(
    r"\b(?:av\.?|avenida|calle|pasaje|psje\.?|camino|villa|población|poblacion)\b"
    r"[^\n,;]{0,60}?\d{1,5}\b",
    re.IGNORECASE,
)

# Nombre real: etiqueta explícita seguida de un nombre propio (una o más
# palabras capitalizadas). Ej.: ``Nombre: Juan Pérez``, ``el niño Mateo
# González``. Deliberadamente conservador (requiere una etiqueta) para no
# marcar como nombre cualquier palabra capitalizada del texto pedagógico.
# La etiqueta es *case-insensitive* (``(?i:...)``), pero el valor del nombre se
# exige capitalizado para no confundir palabras comunes con nombres propios.
_NOMBRE_ETIQUETADO = re.compile(
    r"(?i:\b(?:nombre|nombres|apellido|apellidos|se\s+llama|llamad[oa]|"
    r"niñ[oa]|niño/a|alumn[oa]|estudiante|paciente)\b)"
    r"\s*[:\-]?\s*"
    r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})",
)

# El identificador seudónimo ``id_nino`` del dataset E-1 (p. ej. ``N-00042``,
# ``NINO_0001``): es seguro y NUNCA debe tratarse como dato sensible.
_ID_NINO_SEGURO = re.compile(r"\b(?:N-?\d{3,}|NINO[_-]?\d{3,})\b", re.IGNORECASE)


class GuardiaDespersonalizacion:
    """Inspecciona texto en busca de datos directamente identificatorios (11.3).

    Es *stateless* y reutilizable: una sola instancia puede inspeccionar
    cualquier número de textos. No conoce el LLM ni la capa HTTP (SRP).
    """

    def inspeccionar(self, texto: str) -> Hallazgo:
        """Devuelve las categorías de dato sensible presentes en ``texto``.

        Categorías posibles: ``"rut"``, ``"direccion"``, ``"contacto"``,
        ``"nombre"``. El identificador seudónimo ``id_nino`` se neutraliza antes
        de analizar para evitar falsos positivos.
        """
        if not texto:
            return Hallazgo(categorias=())

        # Neutralizar los id_nino seudónimos para que no disparen patrones de
        # contacto/nombre (p. ej. que un ``N-0009...`` se lea como teléfono).
        limpio = _ID_NINO_SEGURO.sub(" ", texto)

        categorias: list[str] = []
        if _RUT.search(limpio):
            categorias.append("rut")
        if _DIRECCION.search(limpio):
            categorias.append("direccion")
        if _EMAIL.search(limpio) or _TELEFONO.search(limpio):
            categorias.append("contacto")
        if _NOMBRE_ETIQUETADO.search(limpio):
            categorias.append("nombre")

        return Hallazgo(categorias=tuple(categorias))

    def exigir_despersonalizado(self, *fragmentos: str) -> None:
        """Bloquea y registra si algún fragmento contiene datos sensibles (11.3).

        Concatena los fragmentos (p. ej. ``prompt`` + ``context``) y los
        inspecciona en conjunto. Si detecta datos no permitidos, **registra el
        evento** (sin volcar el valor sensible) y levanta
        :class:`DatosSensiblesError`, de modo que el envío al LLM se bloquee.

        Args:
            *fragmentos: textos que se enviarían al LLM.

        Raises:
            DatosSensiblesError: si cualquier fragmento contiene nombre real,
                RUT, dirección o dato de contacto.
        """
        texto = "\n".join(f for f in fragmentos if f)
        hallazgo = self.inspeccionar(texto)
        if hallazgo.hay_datos_sensibles:
            # Se registra el EVENTO y las CATEGORÍAS, nunca el valor detectado,
            # para no filtrar el dato sensible al log (Requirement 11.3).
            logger.warning(
                "Envío al LLM bloqueado por el resguardo de datos sensibles: "
                "el contenido contiene datos no permitidos (categorías: %s).",
                ", ".join(hallazgo.categorias),
            )
            raise DatosSensiblesError(list(hallazgo.categorias))


__all__ = [
    "GuardiaDespersonalizacion",
    "DatosSensiblesError",
    "Hallazgo",
]
