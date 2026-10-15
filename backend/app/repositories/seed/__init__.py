"""Seed del dataset sintético E-1 para la base relacional (Capa 3).

Expone :func:`seed` para cargar el dataset E-1 en la base relacional de forma
idempotente, y :func:`cargar_distribucion_y_validacion` / el atributo perezoso
``DISTRIBUCION_Y_VALIDACION`` con los conteos esperados por tabla (fuente de
verdad para los tests de conteo).
"""

from app.repositories.seed.seed import (
    cargar_dataset,
    cargar_distribucion_y_validacion,
    seed,
)

__all__ = [
    "seed",
    "cargar_dataset",
    "cargar_distribucion_y_validacion",
    "DISTRIBUCION_Y_VALIDACION",
]


def __getattr__(name: str):
    """Reexporta perezosamente ``DISTRIBUCION_Y_VALIDACION`` (PEP 562)."""
    if name == "DISTRIBUCION_Y_VALIDACION":
        return cargar_distribucion_y_validacion()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
