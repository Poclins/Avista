"""Router de salud (Módulo G, tarea 9.3).

Endpoint del contrato REST (ver design.md §API):

- ``GET /health``   salud para API Gateway / demo. Responde 200 y expone el
  modo de ejecución (``use_mocks``) y el entorno.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas import HealthOut
from app.core.config import Settings, get_settings

router = APIRouter(tags=["infra"])


@router.get("/health", response_model=HealthOut, summary="Health check")
def health(config: Settings = Depends(get_settings)) -> HealthOut:
    """Confirma que la app está viva y en qué modo corre (Requirement 10.5)."""
    return HealthOut(
        status="ok",
        app=config.app_name,
        use_mocks=config.use_mocks,
        environment=config.environment,
    )


__all__ = ["router"]
