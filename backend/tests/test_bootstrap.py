"""Pruebas del bootstrap idempotente del filesystem Lambda."""

from pathlib import Path

from app.core.bootstrap import bootstrap_runtime
from app.core.config import Settings


def _settings(seed: Path, destination: Path, storage: Path) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{destination.as_posix()}",
        demo_seed_db_path=str(seed),
        local_storage_dir=str(storage),
    )


def test_bootstrap_copia_seed_y_crea_storage(tmp_path: Path) -> None:
    seed = tmp_path / "seed.db"
    seed.write_bytes(b"seed-limpio")
    destination = tmp_path / "runtime" / "jaimes.db"
    storage = tmp_path / "storage"

    bootstrap_runtime(_settings(seed, destination, storage))

    assert destination.read_bytes() == b"seed-limpio"
    assert storage.is_dir()


def test_bootstrap_reinvocado_no_sobrescribe_cambios(tmp_path: Path) -> None:
    seed = tmp_path / "seed.db"
    seed.write_bytes(b"seed-limpio")
    destination = tmp_path / "jaimes.db"
    settings = _settings(seed, destination, tmp_path / "storage")
    bootstrap_runtime(settings)
    destination.write_bytes(b"cambios-runtime")

    bootstrap_runtime(settings)

    assert destination.read_bytes() == b"cambios-runtime"


def test_bootstrap_restaura_seed_en_entorno_nuevo(tmp_path: Path) -> None:
    seed = tmp_path / "seed.db"
    seed.write_bytes(b"seed-limpio")
    first = tmp_path / "env-1" / "jaimes.db"
    second = tmp_path / "env-2" / "jaimes.db"

    bootstrap_runtime(_settings(seed, first, tmp_path / "storage-1"))
    first.write_bytes(b"modificada")
    bootstrap_runtime(_settings(seed, second, tmp_path / "storage-2"))

    assert first.read_bytes() == b"modificada"
    assert second.read_bytes() == b"seed-limpio"
