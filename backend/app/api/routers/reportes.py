"""Router del reporte de dirección (Módulo G, tarea 9.3).

Endpoint del contrato REST (ver design.md §API):

- ``GET /jardines/{id}/reportes``   generar/obtener el reporte de dirección de
  un jardín para un período (Requirement 7.1).

El período se recibe por *query params* ``fecha_inicio`` y ``fecha_fin`` (ambas
inclusivas, formato ISO AAAA-MM-DD). El ``DirectorReportService`` agrega todas
las métricas vía ``RelationalRepo`` (SQL) y el LLM solo narra el resumen; un
rango inválido (``inicio > fin``) lo traduce a 422 el manejador global de
errores (:mod:`app.api.errors`, tarea 9.4; Requirement 7.2).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api import mappers
from app.api.schemas import ReporteOut
from app.core.container import get_director_report_service
from app.services.director_report_service import DirectorReportService

router = APIRouter(prefix="/jardines", tags=["reportes"])


@router.get(
    "/{id_jardin}/reportes",
    response_model=ReporteOut,
    summary="Generar/obtener el reporte de dirección de un jardín",
)
def reporte_direccion(
    id_jardin: str,
    fecha_inicio: date = Query(..., description="Inicio del período (ISO)"),
    fecha_fin: date = Query(..., description="Fin del período (ISO, inclusive)"),
    reportes: DirectorReportService = Depends(get_director_report_service),
) -> ReporteOut:
    """Genera el reporte de dirección agregado del jardín para el período.

    Un jardín/sala sin datos produce un reporte con conteos en cero sin error
    (Requirement 7.7); un rango de fechas inválido se rechaza con 422
    (Requirement 7.2).
    """
    # ``ReporteRangoInvalidoError`` (rango inválido → 422, Requirement 7.2) se
    # traduce en el manejador global de errores (tarea 9.4).
    resultado = reportes.generar(
        id_jardin=id_jardin,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    return mappers.reporte_out(resultado)


__all__ = ["router"]
