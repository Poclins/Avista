"""Seed del Dataset E-1 para la base relacional (Capa 3).

Expone :func:`seed_oficial` para cargar la **fuente de verdad** (Dataset E-1
oficial) desde el zip público ``dataset_e1_publico.zip`` vía ``DatasetLoader``,
validando los conteos contra ``distribucion_y_validacion`` (y rechazando con
error en español si alguno no coincide), y :func:`seed` para el dataset
reducido/casero (solo respaldo rápido de pruebas). ``DatasetLoader`` queda
encapsulado tras esta frontera del seed.
"""

from app.repositories.seed.dataset_loader import (
    DatasetE1,
    DatasetLoader,
    DatasetLoaderError,
)
from app.repositories.seed.seed import (
    SeedError,
    SeedValidationError,
    cargar_dataset,
    cargar_distribucion_y_validacion,
    conteos_esperados,
    seed,
    seed_oficial,
    validar_conteos,
)

__all__ = [
    "seed",
    "seed_oficial",
    "conteos_esperados",
    "validar_conteos",
    "SeedError",
    "SeedValidationError",
    "cargar_dataset",
    "cargar_distribucion_y_validacion",
    "DISTRIBUCION_Y_VALIDACION",
    "DatasetLoader",
    "DatasetE1",
    "DatasetLoaderError",
]


def __getattr__(name: str):
    """Reexporta perezosamente ``DISTRIBUCION_Y_VALIDACION`` (PEP 562)."""
    if name == "DISTRIBUCION_Y_VALIDACION":
        return cargar_distribucion_y_validacion()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
