"""Endpoints de educadoras para selección guiada en el frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api import mappers
from app.api.schemas import EducadoraOut, NinoOut
from app.core.container import get_relational_repo
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import Educadora as EducadoraORM, Nino as NinoORM

router = APIRouter(prefix="/educadoras", tags=["educadoras"])


@router.get("", response_model=list[EducadoraOut])
def listar_educadoras(
    repo: RelationalRepo = Depends(get_relational_repo),
) -> list[EducadoraOut]:
    """Lista las educadoras disponibles en el dataset E-1."""
    educadoras = sorted(repo.list(EducadoraORM), key=lambda e: e.id_educadora)
    return [mappers.educadora_out(educadora) for educadora in educadoras]


@router.get("/{id_educadora}/ninos", response_model=list[NinoOut])
def listar_ninos_de_educadora(
    id_educadora: str,
    repo: RelationalRepo = Depends(get_relational_repo),
) -> list[NinoOut]:
    """Lista todos los niños/as del jardín al que pertenece la educadora.

    El Dataset E-1 no incluye una tabla de asignación educadora-niño. La
    relación válida disponible es el jardín compartido, que además permite
    capturar la primera observación de un niño que aún no tenga registros.
    """
    educadora = repo.get(EducadoraORM, id_educadora)
    if educadora is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la educadora con id={id_educadora!r}.",
        )

    ninos = sorted(
        (
            nino
            for nino in repo.list(NinoORM)
            if nino.id_jardin == educadora.id_jardin
        ),
        key=lambda nino: (nino.sala_grupo, nino.id_nino),
    )
    return [mappers.nino_out(nino) for nino in ninos]


__all__ = ["router"]
