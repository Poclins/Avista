"""Routers REST de la API (Módulo G, tarea 9.3).

Reúne los routers de dominio del contrato REST para que ``app.main`` los incluya
en la aplicación FastAPI. Cada router es un módulo delgado que valida con
Pydantic y delega en los servicios de la Capa 2 vía el contenedor de DI.
"""

from app.api.routers import (
    bitacoras,
    educadoras,
    health,
    ninos,
    observaciones,
    recomendaciones,
    reportes,
    ruta_niveles,
)

# Orden de inclusión en la app. Los routers de niños/observaciones comparten
# prefijos de ruta (``/ninos/{id}/...``); FastAPI resuelve cada operación por
# método + patrón, por lo que el orden no genera colisiones.
all_routers = [
    health.router,
    educadoras.router,
    ninos.router,
    observaciones.router,
    bitacoras.router,
    recomendaciones.router,
    reportes.router,
    ruta_niveles.router,
]

__all__ = [
    "all_routers",
    "bitacoras",
    "educadoras",
    "health",
    "ninos",
    "observaciones",
    "recomendaciones",
    "reportes",
    "ruta_niveles",
]
