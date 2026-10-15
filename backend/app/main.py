"""Punto de entrada de la API de jAImes (FastAPI).

Esta es la base de la Capa 2 (lógica de negocio). Por ahora solo expone un
health check; los routers de dominio (ninos, observaciones, bitácoras,
recomendaciones, reportes) se añaden en tareas posteriores.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI

from app.core.config import Settings, get_settings


def create_app() -> FastAPI:
    """Construye y configura la instancia de la aplicación FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title="jAImes API",
        description=(
            "De la observación a la acción: IA para el desarrollo infantil "
            "(Fundación Integra · AWS Breaking Barriers Chile 2026). "
            "Datos sintéticos y seudonimizados; no es instrumento clínico."
        ),
        version="0.1.0",
    )

    @app.get("/health", tags=["infra"])
    def health(config: Settings = Depends(get_settings)) -> dict[str, object]:
        """Health check: confirma que la app está viva y en qué modo corre."""
        return {
            "status": "ok",
            "app": config.app_name,
            "use_mocks": config.use_mocks,
            "environment": config.environment,
        }

    return app


app = create_app()
