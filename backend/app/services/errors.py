"""Excepciones tipadas de la capa de servicios (Capa 2).

Los servicios traducen fallos de infraestructura (repositorios, proveedores) a
estas excepciones de dominio con **mensajes en español**, de modo que la capa de
API (Módulo G) las convierta a respuestas HTTP sin filtrar detalles sensibles
(Requirements 3.6, 10.6). Son independientes de los errores de proveedores de IA
de :mod:`app.providers.errors`.

Jerarquía:
- ``ServiceError`` — raíz común de los fallos de la capa de servicios.
  - ``PersistenciaError`` — fallo al persistir mediante un repositorio
    (p. ej. ``RelationalRepo``); se conservan los valores previos sin aplicar
    cambios parciales (Requirement 3.6).
"""

from __future__ import annotations


class ServiceError(Exception):
    """Error base de la capa de servicios con un mensaje en español."""


class PersistenciaError(ServiceError):
    """Fallo al persistir en un repositorio sin aplicar cambios parciales.

    Se usa cuando la escritura mediante ``RelationalRepo`` (u otro repositorio)
    falla: el estado anterior se conserva intacto y se devuelve un mensaje en
    español (Requirement 3.6).
    """


__all__ = [
    "ServiceError",
    "PersistenciaError",
]
