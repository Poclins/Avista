"""Manejo centralizado de errores de la API en español (Módulo G, tarea 9.4).

Registra *exception handlers* globales de FastAPI que traducen las excepciones
tipadas del dominio (servicios de la Capa 2) y de los proveedores de IA
(:mod:`app.providers.errors`) a respuestas HTTP con un **cuerpo uniforme en
español**, sin filtrar detalles sensibles (Requirement 10.6).

Diseño:

- **Cuerpo uniforme**: ``{"detail": "<mensaje en español>"}`` — la misma forma
  que ya usan los routers con ``HTTPException``, de modo que clientes y tests
  no distingan si el error se tradujo en el router o aquí.
- **Mapa de códigos** (Requirements 1.3, 2.6, 5.2, 5.4, 5.9, 10.6):
  - **400** entrada/formato inválido (``IngestionValidationError``,
    ``RecommendationValidationError``).
  - **404** recurso no encontrado (``BitacoraNoEncontradaError``,
    ``RecommendationError``, ``PersistenciaError`` de "no existe").
  - **409** conflicto con el estado actual (``BitacoraConflictoError``).
  - **422** validación / sin evidencia / datos no permitidos
    (``BitacoraSinEvidenciaError``, ``ReporteRangoInvalidoError``,
    ``DatosSensiblesError``, ``PersistenciaError`` genérico).
  - **503** fallo del LLM o de un proveedor de IA (``BitacoraLlmError``,
    ``LlmError``/``ProviderError``).
- **Sanitización**: los errores crudos de proveedor/AWS
  (``ProviderError`` y subclases levantadas directamente, sin pasar por un
  error de servicio con mensaje en español) **nunca** se devuelven al cliente:
  se **registra** el detalle real (CloudWatch en producción) y se responde un
  mensaje genérico en español (Requirement 10.6).

Estos handlers actúan como **red de seguridad global**: los routers pueden
seguir traduciendo los errores que ya manejan (tarea 9.3); si una excepción
tipada se escapa de un router, aquí recibe el mismo código y la misma forma de
respuesta, de forma consistente en toda la app.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.despersonalizacion import DatosSensiblesError
from app.providers.errors import (
    EmbeddingError,
    LlmError,
    ProviderError,
    TranscriptionError,
)
from app.services.bitacora_service import (
    BitacoraConflictoError,
    BitacoraLlmError,
    BitacoraNoEncontradaError,
    BitacoraSinEvidenciaError,
)
from app.services.director_report_service import ReporteRangoInvalidoError
from app.services.errors import PersistenciaError
from app.services.ingestion_service import IngestionValidationError
from app.services.recommendation_service import (
    RecommendationError,
    RecommendationValidationError,
)

logger = logging.getLogger("jaimes.api.errors")

# Mensaje genérico en español para fallos de proveedores de IA/AWS: se devuelve
# al cliente en lugar del error crudo del SDK para no filtrar detalles sensibles
# (Requirement 10.6). El detalle real se registra, no se expone.
_MENSAJE_PROVEEDOR_GENERICO = (
    "El servicio de inteligencia artificial no está disponible en este "
    "momento. Intente nuevamente más tarde."
)

# Marcador que distingue un ``PersistenciaError`` de "recurso inexistente"
# (→ 404) de un fallo de persistencia genérico (→ 422). Los servicios redactan
# el mensaje en español con esta frase cuando el recurso no existe.
_FRASE_NO_EXISTE = "no existe"


def _respuesta(status_code: int, detalle: str) -> JSONResponse:
    """Construye la respuesta JSON uniforme en español ``{"detail": ...}``."""
    return JSONResponse(status_code=status_code, content={"detail": detalle})


def registrar_manejadores_errores(app: FastAPI) -> None:
    """Registra en la app los *exception handlers* globales en español.

    Se invoca desde ``create_app`` para que el mapeo aplique a toda la
    aplicación (uvicorn local y Lambda por igual), sin que cada router repita la
    traducción (tarea 9.4).
    """

    # --- 400 · Entrada/formato inválido (Requirements 1.3, 2.6) ---------------
    @app.exception_handler(IngestionValidationError)
    async def _ingestion_invalida(
        _request: Request, exc: IngestionValidationError
    ) -> JSONResponse:
        return _respuesta(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.exception_handler(RecommendationValidationError)
    async def _recomendacion_invalida(
        _request: Request, exc: RecommendationValidationError
    ) -> JSONResponse:
        return _respuesta(status.HTTP_400_BAD_REQUEST, str(exc))

    # --- 404 · Recurso no encontrado (Requirement 10.6) -----------------------
    @app.exception_handler(BitacoraNoEncontradaError)
    async def _bitacora_no_encontrada(
        _request: Request, exc: BitacoraNoEncontradaError
    ) -> JSONResponse:
        return _respuesta(status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(RecommendationError)
    async def _recomendacion_no_encontrada(
        _request: Request, exc: RecommendationError
    ) -> JSONResponse:
        # ``RecommendationValidationError`` (400) es subclase y tiene su propio
        # handler más específico; aquí llega solo el ``RecommendationError``
        # base, que el servicio usa para "no encontrado" (niño/a o rúbrica).
        return _respuesta(status.HTTP_404_NOT_FOUND, str(exc))

    # --- 409 · Conflicto con el estado actual (Requirement 5.9) ---------------
    @app.exception_handler(BitacoraConflictoError)
    async def _bitacora_conflicto(
        _request: Request, exc: BitacoraConflictoError
    ) -> JSONResponse:
        return _respuesta(status.HTTP_409_CONFLICT, str(exc))

    # --- 422 · Validación / sin evidencia (Requirements 5.2, 7.2) -------------
    @app.exception_handler(BitacoraSinEvidenciaError)
    async def _bitacora_sin_evidencia(
        _request: Request, exc: BitacoraSinEvidenciaError
    ) -> JSONResponse:
        return _respuesta(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    @app.exception_handler(ReporteRangoInvalidoError)
    async def _reporte_rango_invalido(
        _request: Request, exc: ReporteRangoInvalidoError
    ) -> JSONResponse:
        return _respuesta(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    @app.exception_handler(DatosSensiblesError)
    async def _datos_sensibles(
        _request: Request, exc: DatosSensiblesError
    ) -> JSONResponse:
        # Resguardo de datos sensibles (Requirement 11.3): el envío al LLM se
        # bloqueó porque el contenido contiene datos no permitidos. El mensaje
        # ya está en español y NO incluye el valor sensible; las categorías se
        # registran para trazabilidad sin exponer el dato.
        logger.warning(
            "Solicitud bloqueada por el resguardo de datos sensibles "
            "(categorías: %s).",
            ", ".join(exc.categorias),
        )
        return _respuesta(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    @app.exception_handler(PersistenciaError)
    async def _persistencia(
        _request: Request, exc: PersistenciaError
    ) -> JSONResponse:
        # El servicio redacta el mensaje en español; "no existe" ⇒ 404, el resto
        # ⇒ 422 (los valores previos se conservan, Requirement 3.6).
        detalle = str(exc)
        codigo = (
            status.HTTP_404_NOT_FOUND
            if _FRASE_NO_EXISTE in detalle.lower()
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        return _respuesta(codigo, detalle)

    # --- 503 · Fallo del LLM / proveedor de IA (Requirement 5.4) --------------
    @app.exception_handler(BitacoraLlmError)
    async def _bitacora_llm(
        _request: Request, exc: BitacoraLlmError
    ) -> JSONResponse:
        # ``BitacoraLlmError`` lleva un mensaje en español redactado por el
        # servicio (seguro de exponer); el detalle crudo del proveedor ya fue
        # traducido en la Capa 2. Aun así registramos para trazabilidad.
        logger.warning("Fallo del LLM al generar bitácora: %s", exc)
        return _respuesta(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))

    @app.exception_handler(ProviderError)
    async def _proveedor_ia(_request: Request, exc: ProviderError) -> JSONResponse:
        # Error crudo de un proveedor de IA/AWS que se escapó sin traducir
        # (``LlmError``, ``TranscriptionError``, ``EmbeddingError`` o la base
        # ``ProviderError``). NO se expone el detalle real: se registra para
        # CloudWatch y se responde un mensaje genérico en español
        # (Requirement 10.6).
        logger.error(
            "Error no controlado del proveedor de IA (%s): %s",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return _respuesta(
            status.HTTP_503_SERVICE_UNAVAILABLE, _MENSAJE_PROVEEDOR_GENERICO
        )

    # Nota: ``TranscriptionError``, ``EmbeddingError`` y ``LlmError`` son
    # subclases de ``ProviderError``; FastAPI despacha por la clase registrada
    # más cercana en la jerarquía, por lo que el handler de ``ProviderError``
    # los cubre con sanitización. Se referencian explícitamente para dejar
    # constancia del contrato (tarea 9.4) y evitar imports sin uso.
    _ = (TranscriptionError, EmbeddingError, LlmError)


__all__ = ["registrar_manejadores_errores"]
