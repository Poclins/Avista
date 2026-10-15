"""Interfaz del proveedor de transcripción (puerto del Modelo 1, Capa 2).

Define el contrato que el ``TranscriptionService`` (Módulo D) usa para convertir
medios (audio, video, foto de nota manuscrita) en texto en español, sin acoplarse
a ningún SDK de AWS (Requirement 2.8, principio DIP). Las implementaciones
concretas enrutan por ``formato``: audio/video → Transcribe, foto → Textract
(OCR), video → además metadatos de escena de Rekognition en el camino AWS
primario; la implementación mock deriva texto plausible del dataset E-1
(Requirements 2.1–2.4).

Son intercambiables (LSP) y se seleccionan por la configuración ``USE_MOCKS``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import FormatoCaptura


class TranscriptionProvider(ABC):
    """Puerto de transcripción/extracción de texto (Modelo 1).

    Las implementaciones AWS (primaria) y mock (secundaria) deben ser
    intercambiables: el comportamiento observable no depende del proveedor.
    """

    @abstractmethod
    def transcribe(self, media_ref: str, formato: FormatoCaptura) -> str:
        """Transcribe o extrae el texto de un medio y lo devuelve en español.

        Args:
            media_ref: referencia al medio ya almacenado (p. ej. clave S3 o ruta
                local devuelta por ``StorageRepo.put``).
            formato: formato del medio, que determina el enrutamiento del
                proveedor (audio/video → voz a texto; foto → OCR).

        Returns:
            El texto resultante de la transcripción/extracción.

        Raises:
            TranscriptionError: si el medio es inválido o la transcripción falla
                o excede su plazo máximo tras los reintentos (Requirements 2.6,
                2.7).
        """


__all__ = ["TranscriptionProvider"]
