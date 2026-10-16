"""Routers de niños/as (Módulo G, tarea 9.3).

Endpoints del contrato REST (ver design.md §API):

- ``GET /ninos/{id}``        ficha + trayectoria del niño/a.
- ``GET /ninos?sala=...``    "Mi sala": niños/as de una sala de un jardín.

Son lecturas puras: consultan el ``RelationalRepo`` vía ``Depends(...)`` y dan
forma a la respuesta con los mappers, sin lógica de negocio en el router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import mappers
from app.api.schemas import FichaNinoOut, NinoOut
from app.core.container import get_relational_repo
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import Nino as NinoORM

router = APIRouter(prefix="/ninos", tags=["ninos"])


@router.get(
    "",
    response_model=list[NinoOut],
    summary='"Mi sala": niños/as de una sala de un jardín',
)
def listar_mi_sala(
    jardin: str = Query(..., min_length=1, description="id_jardin del jardín"),
    sala: str = Query(..., min_length=1, description="sala_grupo a listar"),
    repo: RelationalRepo = Depends(get_relational_repo),
) -> list[NinoOut]:
    """Lista los niños/as de una sala concreta de un jardín (Requirement 8.2).

    El contrato muestra ``GET /ninos?sala=...``; para identificar la sala sin
    ambigüedad se requiere también el ``jardin`` (una ``sala_grupo`` pertenece a
    un jardín). Devuelve una lista vacía si no hay niños/as en esa sala.
    """
    ninos = repo.ninos_por_sala(jardin, sala)
    return [mappers.nino_out(n) for n in ninos]


@router.get(
    "/{id_nino}",
    response_model=FichaNinoOut,
    summary="Ficha de un niño/a con su trayectoria",
)
def ficha_nino(
    id_nino: str,
    repo: RelationalRepo = Depends(get_relational_repo),
) -> FichaNinoOut:
    """Devuelve la ficha del niño/a + su trayectoria de observaciones.

    Responde 404 en español si el niño/a no existe (Requirement 10.6).
    """
    nino = repo.get(NinoORM, id_nino)
    if nino is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el niño/a con id_nino={id_nino!r}.",
        )
    observaciones = repo.observaciones_de_nino(id_nino)
    return mappers.ficha_nino_out(nino, observaciones)


__all__ = ["router"]
