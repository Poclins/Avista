"""Router de la ruta/rúbrica de referencia (Módulo G, tarea 9.3).

Endpoint del contrato REST (ver design.md §API):

- ``GET /ruta-niveles``   rúbrica/ruta de referencia (niveles 1–9 + versión de
  rúbrica vigente).

Lectura pura: lista los niveles de ``ruta_niveles`` vía ``RelationalRepo`` y
expone la versión de la rúbrica vigente para que el frontend muestre la ruta de
desarrollo de referencia.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api import mappers
from app.api.schemas import RutaNivelesOut
from app.core.container import get_relational_repo
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import RutaNivel as RutaNivelORM

router = APIRouter(tags=["ruta-niveles"])


@router.get(
    "/ruta-niveles",
    response_model=RutaNivelesOut,
    summary="Ruta/rúbrica de referencia (niveles 1–9 + rúbrica vigente)",
)
def ruta_niveles(
    repo: RelationalRepo = Depends(get_relational_repo),
) -> RutaNivelesOut:
    """Devuelve los niveles de la ruta de desarrollo y la rúbrica vigente."""
    niveles = repo.list(RutaNivelORM)
    vigente = repo.rubrica_vigente()
    version = vigente.version_rubrica if vigente is not None else None
    return mappers.ruta_niveles_out(niveles, version)


__all__ = ["router"]
