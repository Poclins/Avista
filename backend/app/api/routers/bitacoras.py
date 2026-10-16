"""Routers de bitácoras quincenales (Módulo G, tarea 9.3).

Endpoints del contrato REST (ver design.md §API):

- ``POST  /ninos/{id}/bitacoras``   generar bitácora quincenal (body: período).
- ``GET   /ninos/{id}/bitacoras``   listar bitácoras del niño/a.
- ``PATCH /bitacoras/{id}``         editar (borrador) o aprobar (Requirements
  5.7, 5.8, 5.9).

Los routers delegan en el ``BitacoraService`` vía ``Depends(...)``. Los errores
tipados del servicio (sin evidencia → 422, LLM caído → 503, no encontrada →
404, conflicto por aprobada → 409) los traduce de forma uniforme el manejador
global de :mod:`app.api.errors` (tarea 9.4), conservando el mensaje en español
del servicio; el router solo valida la forma de la entrada.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api import mappers
from app.api.schemas import BitacoraEditarIn, BitacoraGenerarIn, BitacoraOut
from app.core.container import get_bitacora_service, get_relational_repo
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import Nino as NinoORM
from app.services.bitacora_service import BitacoraService

router = APIRouter(tags=["bitacoras"])


@router.post(
    "/ninos/{id_nino}/bitacoras",
    response_model=BitacoraOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generar la bitácora quincenal de un niño/a",
)
def generar_bitacora(
    id_nino: str,
    cuerpo: BitacoraGenerarIn,
    bitacoras: BitacoraService = Depends(get_bitacora_service),
) -> BitacoraOut:
    """Genera y persiste (en borrador) la bitácora quincenal de un niño/a.

    Aborta con 422 si no hay evidencia en el período (Requirement 5.2) y con
    503 si el LLM falla o excede su plazo (Requirement 5.4).
    """
    if cuerpo.fecha_inicio > cuerpo.fecha_fin:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "El rango del período es inválido: la fecha de inicio no puede "
                "ser posterior a la fecha de fin."
            ),
        )
    # ``BitacoraSinEvidenciaError`` (→ 422) y ``BitacoraLlmError`` (→ 503) se
    # traducen en los manejadores globales de errores (tarea 9.4).
    bitacora = bitacoras.generar(
        id_nino=id_nino,
        id_educadora=cuerpo.id_educadora,
        fecha_inicio=cuerpo.fecha_inicio,
        fecha_fin=cuerpo.fecha_fin,
    )

    return mappers.bitacora_out(bitacora)


@router.get(
    "/ninos/{id_nino}/bitacoras",
    response_model=list[BitacoraOut],
    summary="Listar las bitácoras de un niño/a",
)
def listar_bitacoras(
    id_nino: str,
    repo: RelationalRepo = Depends(get_relational_repo),
) -> list[BitacoraOut]:
    """Lista las bitácoras del niño/a ordenadas por fecha ascendente."""
    if repo.get(NinoORM, id_nino) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el niño/a con id_nino={id_nino!r}.",
        )
    return [mappers.bitacora_out(b) for b in repo.bitacoras_de_nino(id_nino)]


@router.patch(
    "/bitacoras/{id_bitacora}",
    response_model=BitacoraOut,
    summary="Editar (borrador) o aprobar una bitácora",
)
def actualizar_bitacora(
    id_bitacora: str,
    cuerpo: BitacoraEditarIn,
    bitacoras: BitacoraService = Depends(get_bitacora_service),
) -> BitacoraOut:
    """Edita el texto de una bitácora en borrador o la aprueba.

    - ``accion="editar"``: requiere ``texto`` y solo aplica en borrador; una
      bitácora aprobada es inmutable y se rechaza con 409 (Requirement 5.9).
    - ``accion="aprobar"``: cambia el estado a aprobada (Requirement 5.8).
    """
    # ``BitacoraNoEncontradaError`` (→ 404) y ``BitacoraConflictoError`` (→ 409,
    # bitácora aprobada inmutable) se traducen en los manejadores globales de
    # errores (tarea 9.4). El router solo valida la forma de la entrada.
    if cuerpo.accion == "editar":
        if cuerpo.texto is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para editar una bitácora debe indicar el 'texto'.",
            )
        bitacora = bitacoras.editar(id_bitacora, cuerpo.texto)
    else:  # "aprobar"
        bitacora = bitacoras.aprobar(id_bitacora)

    return mappers.bitacora_out(bitacora)


__all__ = ["router"]
