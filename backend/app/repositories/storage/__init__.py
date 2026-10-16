"""Repositorio de almacenamiento (Capa 3): interfaz + adaptadores S3/local."""

from app.repositories.storage.base import (
    MAX_URL_EXPIRY_SECONDS,
    StorageRepo,
    StoredFile,
)
from app.repositories.storage.local_storage import LocalStorageRepo
from app.repositories.storage.s3_storage import S3StorageRepo

__all__ = [
    "StorageRepo",
    "StoredFile",
    "MAX_URL_EXPIRY_SECONDS",
    "LocalStorageRepo",
    "S3StorageRepo",
]
