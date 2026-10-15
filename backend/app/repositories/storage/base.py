"""Interfaz del repositorio de almacenamiento de medios (puerto de la Capa 3).

Define el contrato que el ``IngestionService`` (Módulo D) usa para guardar el
archivo original de una observación no textual y obtener una URL de acceso, sin
acoplarse a ningún SDK (Requirements 1.2, 11.4, principio DIP). La implementación
primaria usa Amazon S3 (cifrado en reposo y URLs prefirmadas de vigencia breve);
la secundaria usa almacenamiento local tras la misma interfaz.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO

# Vigencia máxima de una URL prefirmada: 300 s (Requirement 11.4). Toda URL
# emitida se recorta a este tope aunque se pida una vigencia mayor.
MAX_URL_EXPIRY_SECONDS = 300


@dataclass
class StoredFile:
    """Medio a almacenar: stream binario + nombre original + tipo MIME.

    Es un contenedor liviano para desacoplar la ingesta del framework web: la
    capa de API (Módulo G) adapta el ``UploadFile`` entrante a este tipo, y el
    ``StorageRepo`` consume solo ``stream``/``filename``/``tipo``.

    Attributes:
        stream: contenido binario del medio (file-like con ``read()``).
        filename: nombre original del archivo (se sanea antes de usarlo como ref).
        tipo: tipo MIME del medio (p. ej. ``audio/mpeg``), opcional.
    """

    stream: BinaryIO
    filename: str
    tipo: str | None = None


class StorageRepo(ABC):
    """Puerto de almacenamiento de objetos (medios).

    Las implementaciones (S3 primaria, local secundaria) deben ser
    intercambiables (LSP): el comportamiento observable no depende del backend.
    """

    @abstractmethod
    def put(self, file: StoredFile) -> str:
        """Almacena un archivo y devuelve su referencia (``ref``).

        Args:
            file: medio a almacenar (:class:`StoredFile`).

        Returns:
            La referencia opaca del objeto almacenado (p. ej. clave S3 o ruta
            local), que se asocia a la observación creada (Requirement 1.2).
        """

    @abstractmethod
    def get_url(self, ref: str, expires_in: int = MAX_URL_EXPIRY_SECONDS) -> str:
        """Devuelve una URL de acceso para una referencia previamente guardada.

        Args:
            ref: referencia devuelta por ``put``.
            expires_in: vigencia solicitada en segundos; se recorta a
                :data:`MAX_URL_EXPIRY_SECONDS` (Requirement 11.4).

        Returns:
            La URL de acceso al objeto (en AWS, una URL prefirmada temporal).
        """


__all__ = ["StorageRepo", "StoredFile", "MAX_URL_EXPIRY_SECONDS"]
