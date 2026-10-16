"""Preparación idempotente del filesystem efímero del runtime Lambda."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import Settings


def bootstrap_runtime(settings: Settings) -> None:
    """Restaura el seed empaquetado una sola vez y prepara storage local."""
    if not settings.demo_seed_db_path:
        return

    seed_path = Path(settings.demo_seed_db_path)
    if not seed_path.is_file():
        raise FileNotFoundError(f"No existe la base seed empaquetada: {seed_path}")

    database_path_value = make_url(settings.database_url).database
    if not database_path_value:
        raise ValueError("DATABASE_URL debe apuntar a un archivo SQLite.")
    database_path = Path(database_path_value)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    Path(settings.local_storage_dir).mkdir(parents=True, exist_ok=True)

    if database_path.exists():
        return

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=database_path.parent,
            prefix=f".{database_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with seed_path.open("rb") as source:
                shutil.copyfileobj(source, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, database_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


__all__ = ["bootstrap_runtime"]
