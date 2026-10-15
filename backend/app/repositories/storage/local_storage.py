"""Adaptador secundario del :class:`StorageRepo` sobre el sistema de archivos.

Camino local/mock (``USE_MOCKS=true``): guarda los medios en un directorio base
y devuelve una referencia opaca saneada. No depende de AWS. Mantiene el mismo
contrato observable que :class:`S3StorageRepo` (LSP), de modo que la ingesta no
distingue el backend activo.
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from app.repositories.storage.base import (
    MAX_URL_EXPIRY_SECONDS,
    StorageRepo,
    StoredFile,
)

# Caracteres admitidos en el nombre saneado; el resto se reemplaza por "_".
_SANE = re.compile(r"[^A-Za-z0-9._-]")


class LocalStorageRepo(StorageRepo):
    """Almacena medios en ``base_dir`` y los sirve como URLs ``file://``.

    Args:
        base_dir: directorio raíz donde se escriben los objetos. Se crea si no
            existe.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def put(self, file: StoredFile) -> str:
        """Escribe el contenido y devuelve una ref única y saneada."""
        ref = self._sane_ref(file.filename)
        destino = self._base / ref
        with destino.open("wb") as salida:
            shutil.copyfileobj(file.stream, salida)
        return ref

    def get_url(self, ref: str, expires_in: int = MAX_URL_EXPIRY_SECONDS) -> str:
        """Devuelve una URL ``file://`` si la ref existe dentro de ``base_dir``.

        Raises:
            FileNotFoundError: si la ref no existe o intentaría salir del
                directorio base (traspaso de directorio).
        """
        destino = (self._base / ref).resolve()
        base = self._base.resolve()
        # Rechazar traspaso de directorio: la ruta resuelta debe quedar dentro.
        if base != destino and base not in destino.parents:
            raise FileNotFoundError(ref)
        if not destino.is_file():
            raise FileNotFoundError(ref)
        return destino.as_uri()

    @staticmethod
    def _sane_ref(filename: str) -> str:
        """Deriva una ref sin separadores ni espacios, única por ``uuid``."""
        nombre = Path(filename or "medio").name  # descarta componentes de ruta
        nombre = _SANE.sub("_", nombre)
        return f"{uuid.uuid4().hex}_{nombre}"


__all__ = ["LocalStorageRepo"]
