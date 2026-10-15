"""Adaptador **mock** del ``TranscriptionProvider`` (secundario, local/CI).

Deriva texto plausible en español a partir de la referencia del medio
(``media_ref``) y su ``formato``, sin llamar a AWS ni leer el medio real, de
modo que el Módulo D sea verificable en aislamiento (Requirement 2.8). Las
salidas se inspiran en el estilo del dataset E-1 (notas breves de educadoras) y
son **deterministas**: la misma ``media_ref`` produce siempre el mismo texto,
para que los tests sean reproducibles.

Enrutamiento por formato (equivalente observable al camino AWS, Requirements
2.1–2.4):

- ``audio`` / ``video`` → simula una transcripción de voz a texto (es-CL).
- ``foto`` → simula una extracción OCR de una nota manuscrita.
- ``video`` → además incorpora un resumen de **metadatos de escena** (lo que en
  AWS entrega Rekognition), concatenado al texto transcrito.
- ``texto`` → el proveedor no transcribe texto directo; el ``TranscriptionService``
  (tarea 5.3) usa el texto tal cual. Si llega aquí, se devuelve la referencia
  como texto para no romper el contrato.

El mock también simula fallos de forma determinista para poder probar la lógica
de reintentos y la marca de "pendiente de transcripción": si ``media_ref``
contiene el marcador ``"__fail__"`` lanza :class:`TranscriptionError`.
"""

from __future__ import annotations

import hashlib

from app.domain.models import FormatoCaptura
from app.providers.errors import TranscriptionError
from app.providers.transcription.base import TranscriptionProvider

# Marcador que fuerza un fallo determinista del mock (para tests de reintentos).
FAIL_MARKER = "__fail__"

# Bancos de frases plausibles por formato. El índice se elige de forma
# determinista a partir del hash de ``media_ref`` para dar variedad estable.
_FRASES_VOZ: tuple[str, ...] = (
    "La niña apiló tres cubos y nombró cada color en voz alta.",
    "El niño siguió una instrucción de dos pasos sin apoyo gestual.",
    "La niña compartió los materiales con una compañera y esperó su turno.",
    "El niño resolvió un encaje simple por ensayo y acierto.",
    "La niña relató una secuencia breve de lo que hizo en el patio.",
)
_FRASES_OCR: tuple[str, ...] = (
    "Nota de la tía: hoy logró abrochar su delantal sin ayuda.",
    "Nota de la tía: identificó su casillero por la foto y guardó sus cosas.",
    "Nota de la tía: pidió ir al baño usando palabras completas.",
    "Nota de la tía: ayudó a ordenar los juguetes al terminar el juego.",
    "Nota de la tía: reconoció su nombre escrito en la lista de asistencia.",
)
_ESCENAS_VIDEO: tuple[str, ...] = (
    "sala de actividades, mesa de trabajo, bloques de colores",
    "patio exterior, juegos de motricidad, grupo de niños",
    "rincón de lectura, cojines, estantería con libros",
    "zona de arte, pinturas, delantales",
)


def _indice(media_ref: str, modulo: int) -> int:
    """Índice determinista en ``[0, modulo)`` derivado de ``media_ref``."""
    digest = hashlib.sha256(media_ref.encode("utf-8")).hexdigest()
    return int(digest, 16) % modulo


class MockTranscriptionProvider(TranscriptionProvider):
    """Implementación mock e intercambiable del puerto de transcripción."""

    def transcribe(self, media_ref: str, formato: FormatoCaptura) -> str:
        if FAIL_MARKER in media_ref:
            raise TranscriptionError(
                "No se pudo transcribir el medio (fallo simulado del proveedor mock)."
            )

        if formato is FormatoCaptura.foto:
            return _FRASES_OCR[_indice(media_ref, len(_FRASES_OCR))]

        if formato in (FormatoCaptura.audio, FormatoCaptura.video):
            texto = _FRASES_VOZ[_indice(media_ref, len(_FRASES_VOZ))]
            if formato is FormatoCaptura.video:
                escena = _ESCENAS_VIDEO[_indice(media_ref, len(_ESCENAS_VIDEO))]
                texto = f"{texto} [Escena: {escena}.]"
            return texto

        # ``texto`` directo: el proveedor no transcribe; devolver la referencia.
        return media_ref


__all__ = ["MockTranscriptionProvider", "FAIL_MARKER"]
