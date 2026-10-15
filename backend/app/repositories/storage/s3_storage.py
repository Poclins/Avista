"""Adaptador primario del :class:`StorageRepo` sobre Amazon S3.

Camino AWS (``USE_MOCKS=false``): sube el medio original cifrado en reposo
(``AES256``) y emite URLs prefirmadas de vigencia breve (≤300 s) para el acceso
temporal (Requirement 11.4). El cliente S3 de boto3 se inyecta (DIP) para poder
sustituirlo por un doble en pruebas y para que el contenedor de DI lo construya
con región/credenciales.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from app.repositories.storage.base import (
    MAX_URL_EXPIRY_SECONDS,
    StorageRepo,
    StoredFile,
)


class S3StorageRepo(StorageRepo):
    """Almacena medios en un bucket S3 con cifrado en reposo y URLs prefirmadas.

    Args:
        bucket: nombre del bucket de destino.
        client: cliente ``s3`` de boto3 ya construido (inyección, DIP).
        prefix: prefijo opcional de clave (p. ej. ``observaciones``).
    """

    def __init__(self, bucket: str, client: Any, prefix: str | None = None) -> None:
        self._bucket = bucket
        self._client = client
        self._prefix = prefix.strip("/") if prefix else None

    def put(self, file: StoredFile) -> str:
        """Sube el medio cifrado en reposo y devuelve su clave (``ref``)."""
        key = self._build_key(file.filename)
        extra: dict[str, Any] = {"ServerSideEncryption": "AES256"}
        if file.tipo:
            extra["ContentType"] = file.tipo
        self._client.upload_fileobj(file.stream, self._bucket, key, ExtraArgs=extra)
        return key

    def get_url(self, ref: str, expires_in: int = MAX_URL_EXPIRY_SECONDS) -> str:
        """Devuelve una URL prefirmada ``get_object`` con vigencia recortada.

        La vigencia nunca excede :data:`MAX_URL_EXPIRY_SECONDS` (Requirement 11.4).
        """
        expires = min(max(int(expires_in), 1), MAX_URL_EXPIRY_SECONDS)
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": ref},
            ExpiresIn=expires,
        )

    def _build_key(self, filename: str) -> str:
        """Clave única (uuid) con el nombre saneado y el prefijo opcional."""
        nombre = Path(filename or "medio").name.replace("/", "_").replace("\\", "_")
        key = f"{uuid.uuid4().hex}_{nombre}"
        return f"{self._prefix}/{key}" if self._prefix else key


__all__ = ["S3StorageRepo"]
