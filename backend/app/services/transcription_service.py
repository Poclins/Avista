"""``TranscriptionService`` — valida formato/tamaño y enruta por formato (Módulo D).

Caso de uso de la Capa 2 que envuelve el puerto :class:`TranscriptionProvider`
(tarea 5.2) y expone un único punto de entrada, :meth:`TranscriptionService.obtener_texto`,
que la ingesta usa para convertir cualquier medio en texto en español.

Responsabilidades (Requirements 1.4, 2.5, 2.6):

- **Enrutamiento por ``formato_captura``.** El texto directo
  (:attr:`FormatoCaptura.texto`) se usa **tal cual, sin transcripción**
  (Requirement 2.5); audio, foto y video se delegan al ``TranscriptionProvider``
  inyectado (Requirements 2.1–2.4).
- **Validación de formato.** La extensión del archivo debe pertenecer al conjunto
  soportado por su formato (Requirement 1.4): ``texto`` → txt; ``audio`` → mp3,
  m4a, wav; ``foto`` → jpg, jpeg, png; ``video`` → mp4, mov.
- **Validación de tamaño.** Límite general de 100 MB, con límites más estrictos
  por formato: 10 MB para foto y 500 MB para video (Requirement 2.6).
- **Longitud del texto directo.** Entre 1 y 50.000 caracteres (Requirement 2.5).

Cualquier violación se rechaza con :class:`TranscriptionError` y un **mensaje en
español** (Requirement 2.6), la misma excepción tipada que lanzan los
proveedores, para que la Capa G la traduzca a HTTP 400/4xx sin esquemas
paralelos.

El proveedor concreto se **inyecta** (DIP): el servicio nunca instancia un
adaptador AWS o mock, de modo que puede probarse en aislamiento con un doble.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import FormatoCaptura
from app.providers.errors import TranscriptionError
from app.providers.transcription.base import TranscriptionProvider

# ---------------------------------------------------------------------------
# Límites de validación (Requirements 1.4, 2.5, 2.6)
# ---------------------------------------------------------------------------
_MB = 1024 * 1024

# Longitud del texto directo, en caracteres (Requirement 2.5).
TEXTO_MIN_CHARS = 1
TEXTO_MAX_CHARS = 50_000

# Límite de tamaño general y por formato, en bytes (Requirements 1.1/1.4, 2.6).
TAMANO_MAX_GENERAL = 100 * _MB
TAMANO_MAX_POR_FORMATO: dict[FormatoCaptura, int] = {
    FormatoCaptura.foto: 10 * _MB,
    FormatoCaptura.video: 500 * _MB,
    FormatoCaptura.audio: TAMANO_MAX_GENERAL,
}

# Extensiones soportadas por formato (Requirement 1.4). En minúsculas, sin punto.
EXTENSIONES_POR_FORMATO: dict[FormatoCaptura, frozenset[str]] = {
    FormatoCaptura.texto: frozenset({"txt"}),
    FormatoCaptura.audio: frozenset({"mp3", "m4a", "wav"}),
    FormatoCaptura.foto: frozenset({"jpg", "jpeg", "png"}),
    FormatoCaptura.video: frozenset({"mp4", "mov"}),
}


def _mb(num_bytes: int) -> str:
    """Formatea un tamaño en bytes como ``N MB`` para los mensajes de error."""
    return f"{num_bytes // _MB} MB"


@dataclass(frozen=True, slots=True)
class MediaInput:
    """Entrada normalizada para :meth:`TranscriptionService.obtener_texto`.

    Independiente del framework web: la capa de API construye un ``MediaInput``
    a partir del ``multipart``/JSON entrante y lo pasa al servicio.

    Attributes:
        formato: el ``formato_captura`` declarado (texto/audio/foto/video).
        texto: contenido textual directo, solo para ``formato == texto``.
        media_ref: referencia opaca del medio ya almacenado (``StorageRepo.put``),
            para medios no textuales que deben transcribirse.
        filename: nombre o extensión del archivo, usado para validar el formato
            de los medios no textuales (p. ej. ``"nota.jpg"``).
        size_bytes: tamaño del medio en bytes, usado para validar los límites de
            tamaño de los medios no textuales.
    """

    formato: FormatoCaptura
    texto: str | None = None
    media_ref: str | None = None
    filename: str | None = None
    size_bytes: int | None = None


class TranscriptionService:
    """Valida el medio y lo convierte en texto, enrutando por ``formato_captura``.

    El ``TranscriptionProvider`` se inyecta para poder sustituirlo por un mock o
    fake en los tests (DIP); el servicio no conoce ni crea adaptadores concretos.
    """

    def __init__(self, provider: TranscriptionProvider) -> None:
        self._provider = provider

    def obtener_texto(self, media: MediaInput) -> str:
        """Devuelve el texto del medio, transcribiendo si corresponde.

        Args:
            media: la entrada normalizada a procesar.

        Returns:
            El texto en español: el ``texto`` directo tal cual, o el resultado de
            :meth:`TranscriptionProvider.transcribe` para medios no textuales.

        Raises:
            TranscriptionError: si el formato no es soportado, el tamaño excede su
                límite, la longitud del texto directo está fuera de rango, o la
                propia transcripción falla. El mensaje siempre está en español
                (Requirement 2.6).
        """
        if media.formato is FormatoCaptura.texto:
            return self._texto_directo(media)
        return self._transcribir_medio(media)

    # ------------------------------------------------------------------
    # Texto directo (Requirement 2.5) — sin transcripción
    # ------------------------------------------------------------------
    def _texto_directo(self, media: MediaInput) -> str:
        texto = media.texto
        if texto is None:
            raise TranscriptionError(
                "El formato es «texto» pero no se recibió contenido de texto."
            )

        longitud = len(texto)
        if longitud < TEXTO_MIN_CHARS:
            raise TranscriptionError(
                "El texto está vacío; debe tener entre "
                f"{TEXTO_MIN_CHARS} y {TEXTO_MAX_CHARS:_} caracteres."
            )
        if longitud > TEXTO_MAX_CHARS:
            raise TranscriptionError(
                f"El texto tiene {longitud:_} caracteres y excede el máximo de "
                f"{TEXTO_MAX_CHARS:_} caracteres permitido."
            )
        # Texto directo válido: se usa tal cual, sin transcripción.
        return texto

    # ------------------------------------------------------------------
    # Medios no textuales (Requirements 1.4, 2.1–2.4, 2.6)
    # ------------------------------------------------------------------
    def _transcribir_medio(self, media: MediaInput) -> str:
        self._validar_formato(media)
        self._validar_tamano(media)

        if not media.media_ref:
            raise TranscriptionError(
                "No se recibió la referencia del medio almacenado para transcribir."
            )
        # Delegar en el proveedor inyectado; propaga TranscriptionError si falla.
        return self._provider.transcribe(media.media_ref, media.formato)

    @staticmethod
    def _extension(filename: str | None) -> str:
        """Extrae la extensión en minúsculas (sin punto) de un nombre de archivo."""
        if not filename or "." not in filename:
            return ""
        return filename.rsplit(".", 1)[1].strip().lower()

    def _validar_formato(self, media: MediaInput) -> None:
        permitidas = EXTENSIONES_POR_FORMATO[media.formato]
        extension = self._extension(media.filename)
        if extension not in permitidas:
            admitidas = ", ".join(sorted(permitidas))
            recibida = extension or "(desconocida)"
            raise TranscriptionError(
                f"Formato de archivo no soportado para «{media.formato.value}»: "
                f"se recibió «{recibida}»; formatos admitidos: {admitidas}."
            )

    def _validar_tamano(self, media: MediaInput) -> None:
        if media.size_bytes is None:
            raise TranscriptionError(
                "No se pudo determinar el tamaño del medio para validarlo."
            )
        if media.size_bytes <= 0:
            raise TranscriptionError("El medio está vacío (tamaño de 0 bytes).")

        limite = TAMANO_MAX_POR_FORMATO.get(media.formato, TAMANO_MAX_GENERAL)
        if media.size_bytes > limite:
            raise TranscriptionError(
                f"El medio «{media.formato.value}» pesa {_mb(media.size_bytes)} y "
                f"excede el límite de {_mb(limite)} permitido para su formato."
            )


__all__ = [
    "TranscriptionService",
    "MediaInput",
    "TEXTO_MIN_CHARS",
    "TEXTO_MAX_CHARS",
    "TAMANO_MAX_GENERAL",
    "TAMANO_MAX_POR_FORMATO",
    "EXTENSIONES_POR_FORMATO",
]
