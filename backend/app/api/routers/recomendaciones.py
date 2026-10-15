"""Routers de recomendaciones de nivel (Módulo G, tarea 9.3).

Endpoints del contrato REST (ver design.md §API):

- ``POST /ninos/{id}/recomendaciones``       generar recomendación de nivel
  (Requirement 6.1).
- ``POST /recomendaciones/{id}/decision``     registrar la decisión de la
  educadora (Requirement 6.9).

La **rúbrica decide, la IA argumenta y la educadora valida**: el router solo
expone esa separación de responsabilidades del ``RecommendationService``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api import mappers
from app.api.schemas import (
    DecisionEducadoraIn,
    RecomendacionDecisionOut,
    RecomendacionGenerarIn,
    RecomendacionOut,
)
from app.core.container import get_recommendation_service
from app.domain.rubrica import NUCLEO_POR_DEFECTO
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["recomendaciones"])


@router.post(
    "/ninos/{id_nino}/recomendaciones",
    response_model=RecomendacionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generar la recomendación de nivel de un niño/a",
)
def generar_recomendacion(
    id_nino: str,
    cuerpo: RecomendacionGenerarIn,
    recomendaciones: RecommendationService = Depends(get_recommendation_service),
) -> RecomendacionOut:
    """Genera la recomendación de nivel (AVANZAR/MANTENER/RETROCEDER).

    Se abstiene (sin persistir) si el niño/a tiene <5 observaciones
    (Requirement 6.10). Devuelve 404 si el niño/a no existe o no hay rúbrica
    vigente; 400 si falta la educadora de sesión.
    """
    # ``RecommendationValidationError`` (→ 400, falta educadora) y
    # ``RecommendationError`` (→ 404, niño/a o rúbrica inexistente) se traducen
    # en los manejadores globales de errores (tarea 9.4).
    resultado = recomendaciones.recomendar(
        id_nino=id_nino,
        id_educadora=cuerpo.id_educadora,
        nivel_actual=cuerpo.nivel_actual,
        nucleo=cuerpo.nucleo or NUCLEO_POR_DEFECTO,
    )

    return mappers.recomendacion_out(resultado)


@router.post(
    "/recomendaciones/{id_recomendacion}/decision",
    response_model=RecomendacionDecisionOut,
    summary="Registrar la decisión de la educadora sobre una recomendación",
)
def registrar_decision(
    id_recomendacion: str,
    cuerpo: DecisionEducadoraIn,
    recomendaciones: RecommendationService = Depends(get_recommendation_service),
) -> RecomendacionDecisionOut:
    """Registra la decisión humana final (aceptó/rechazó/ajustó) (Requirement 6.9)."""
    # Errores tipados (→ 400 validación, → 404 no encontrada) traducidos por el
    # manejador global de errores (tarea 9.4).
    recomendacion = recomendaciones.registrar_decision_educadora(
        id_recomendacion, cuerpo.decision_educadora
    )

    return RecomendacionDecisionOut(
        id_recomendacion=recomendacion.id_recomendacion,
        id_nino=recomendacion.id_nino,
        id_educadora=recomendacion.id_educadora,
        decision=recomendacion.decision,
        decision_educadora=recomendacion.decision_educadora,
    )


__all__ = ["router"]
