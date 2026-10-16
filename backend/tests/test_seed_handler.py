"""Tests del handler Lambda de seed (tarea 11.3, fix 3).

Verifican el entrypoint ``app.seed_handler.handler`` en su camino de
**invocación directa** (sin custom resource de CloudFormation) contra una base
**SQLite** (sin AWS): debe crear el esquema, sembrar el dataset reducido (al no
existir el zip oficial) y devolver los conteos por tabla. En SQLite se omite el
preparado de pgvector (no hay ``CREATE EXTENSION``), igual que en el handler.

También se verifica que, ante un evento de custom resource (``RequestType``),
el handler devuelve un ``PhysicalResourceId`` estable (para que el *provider
framework* de CDK no dispare un ``Delete`` del recurso anterior en los
``Update``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import app.seed_handler as seed_handler
from app.core.config import Settings


@pytest.fixture()
def sqlite_settings(tmp_path: Path) -> Settings:
    """Settings de demo: SQLite en archivo temporal y zip oficial inexistente."""
    db = tmp_path / "jaimes.db"
    return Settings(
        use_mocks=True,
        database_url=f"sqlite:///{db.as_posix()}",
        dataset_zip_path=str(tmp_path / "no_existe.zip"),
    )


def _patch_settings(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    """Hace que el handler use las ``settings`` dadas (evita leer el entorno)."""
    monkeypatch.setattr(
        "app.core.config.get_settings", lambda: settings, raising=True
    )


def test_handler_directo_siembra_dataset_reducido(
    monkeypatch: pytest.MonkeyPatch, sqlite_settings: Settings
) -> None:
    _patch_settings(monkeypatch, sqlite_settings)

    resultado = seed_handler.handler({}, None)

    assert resultado["ok"] is True
    resumen = resultado["resumen"]
    # Conteos del dataset reducido (distribucion_y_validacion.json).
    assert resumen["manifestaciones"] == 90
    assert resumen["ninos"] == 12
    assert resumen["ruta_niveles"] == 9
    assert resumen["rubrica_versiones"] >= 1


def test_handler_directo_es_idempotente(
    monkeypatch: pytest.MonkeyPatch, sqlite_settings: Settings
) -> None:
    _patch_settings(monkeypatch, sqlite_settings)

    primero = seed_handler.handler({}, None)["resumen"]
    segundo = seed_handler.handler({}, None)["resumen"]
    assert primero == segundo


def test_handler_sqlite_no_prepara_pgvector(
    monkeypatch: pytest.MonkeyPatch, sqlite_settings: Settings
) -> None:
    """En SQLite no debe intentar preparar pgvector (no hay CREATE EXTENSION)."""
    _patch_settings(monkeypatch, sqlite_settings)

    def _boom(*_a, **_k):  # pragma: no cover - no debe invocarse en SQLite
        raise AssertionError("pgvector no debe prepararse en SQLite")

    monkeypatch.setattr(seed_handler, "_preparar_pgvector", _boom)
    resultado = seed_handler.handler({}, None)
    assert resultado["ok"] is True


def test_handler_custom_resource_devuelve_physical_id_estable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un evento de CFN (RequestType) devuelve un PhysicalResourceId estable."""
    llamadas: list[str] = []
    monkeypatch.setattr(
        seed_handler,
        "_ejecutar_seed",
        lambda: (llamadas.append("x") or {"ninos": 12}),
    )

    creado = seed_handler.handler({"RequestType": "Create"}, None)
    actualizado = seed_handler.handler({"RequestType": "Update"}, None)
    borrado = seed_handler.handler({"RequestType": "Delete"}, None)

    assert creado["PhysicalResourceId"] == actualizado["PhysicalResourceId"]
    assert borrado["PhysicalResourceId"] == creado["PhysicalResourceId"]
    # Create y Update siembran; Delete no ejecuta el seed.
    assert len(llamadas) == 2
    assert creado["Data"]["ninos"] == "12"
