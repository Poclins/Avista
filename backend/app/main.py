"""Punto de entrada de la API de jAImes (FastAPI).

Capa 2 (lógica de negocio): la app FastAPI expone el contrato REST del diseño a
través de los routers de ``app.api.routers`` (ninos, observaciones, bitacoras,
recomendaciones, reportes, ruta-niveles, health). Los routers reciben los
servicios por ``Depends(...)`` del contenedor de DI (``app.core.container``), de
modo que la misma app corra en ``uvicorn`` local y en AWS Lambda sin cambios de
código: la diferencia la marca únicamente la configuración (``USE_MOCKS``).

Manejo de errores (tarea 9.4): ``create_app`` registra los manejadores globales
de :mod:`app.api.errors`, que traducen las excepciones tipadas de servicios y
proveedores de IA a respuestas HTTP en español con un cuerpo uniforme, sin
filtrar detalles sensibles (Requirement 10.6).

Despliegue serverless (Requirement 10): la app se envuelve con **Mangum**
(``handler = Mangum(app)``) para ejecutarse en AWS Lambda tras API Gateway, sin
tocar los routers. En local, ``uvicorn app.main:app`` sirve la misma instancia.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from app.api.errors import registrar_manejadores_errores
from app.api.routers import all_routers
from app.core.bootstrap import bootstrap_runtime
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construye y configura la instancia de la aplicación FastAPI.

    Incluye todos los routers del contrato REST. El contenedor de DI resuelve
    las dependencias de cada router de forma perezosa, de modo que importar la
    app no exige red ni credenciales (clave para el arranque de Lambda y para
    los tests con servicios fake que sobrescriben los ``Depends``).
    """
    active_settings = settings or get_settings()
    bootstrap_runtime(active_settings)

    app = FastAPI(
        title="jAImes API",
        description=(
            "De la observación a la acción: IA para el desarrollo infantil "
            "(Fundación Integra · AWS Breaking Barriers Chile 2026). "
            "Datos sintéticos y seudonimizados; no es instrumento clínico."
        ),
        version="0.1.0",
    )

    for router in all_routers:
        app.include_router(router)

    # Manejo centralizado de errores en español (tarea 9.4): traduce las
    # excepciones tipadas de servicios y proveedores de IA a respuestas HTTP
    # uniformes sin filtrar detalles sensibles (Requirement 10.6).
    registrar_manejadores_errores(app)

    if active_settings.frontend_dist_path:
        frontend_dist = Path(active_settings.frontend_dist_path)
        app.mount(
            "/",
            StaticFiles(directory=frontend_dist, html=True),
            name="frontend",
        )

    return app


app = create_app()

# Adaptador ASGI→Lambda: el mismo ``app`` corre en uvicorn (local) y en Lambda
# tras API Gateway mediante este ``handler`` (Requirement 10). No altera los
# routers ni la lógica de negocio.
handler = Mangum(app)
