"""Tests del manejo centralizado de errores en español (Módulo G, tarea 9.4).

Verifican que los manejadores globales de :mod:`app.api.errors` traducen las
excepciones tipadas de servicios y proveedores de IA a:

- el **código HTTP** correcto (400 formato, 404 no encontrado, 422 validación,
  409 conflicto, 503 LLM/proveedor);
- un **cuerpo uniforme en español** ``{"detail": ...}``;
- **sin filtrar detalles sensibles** para errores crudos de proveedor/AWS: el
  cliente recibe un mensaje genérico y el detalle real queda en el log, no en la
  respuesta (Requirement 10.6).

Para probar los handlers de forma aislada se monta una app con rutas de prueba
que simplemente levantan cada excepción; así se ejercita el manejador global sin
depender del cableado concreto de cada router.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import registrar_manejadores_errores
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

# Detalle "sensible" que NUNCA debe aparecer en el cuerpo de la respuesta cuando
# el error proviene de un proveedor de IA/AWS crudo.
_DETALLE_SENSIBLE = (
    "boto3 ThrottlingException: arn:aws:bedrock:us-east-1:123456789012:"
    "model/anthropic.claude · trace-id=abc123 · secret-token=XYZ"
)


def _app_con(exc: Exception) -> TestClient:
    """App mínima cuya única ruta levanta ``exc``; registra los handlers 9.4."""
    app = FastAPI()
    registrar_manejadores_errores(app)

    @app.get("/boom")
    def _boom() -> None:  # pragma: no cover - el cuerpo siempre levanta
        raise exc

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Mapa de códigos: excepción tipada → status HTTP
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("exc", "esperado"),
    [
        (IngestionValidationError("Debe seleccionar un niño/a."), 400),
        (RecommendationValidationError("Falta la educadora de sesión."), 400),
        (BitacoraNoEncontradaError("No se encontró la bitácora."), 404),
        (RecommendationError("No se encontró el niño/a con id_nino='x'."), 404),
        (BitacoraConflictoError("La bitácora ya está aprobada."), 409),
        (BitacoraSinEvidenciaError("No hay evidencia en el período."), 422),
        (ReporteRangoInvalidoError("El rango de fechas es inválido."), 422),
    ],
)
def test_excepcion_tipada_mapea_a_su_codigo(exc, esperado):
    client = _app_con(exc)
    r = client.get("/boom")
    assert r.status_code == esperado
    # Cuerpo uniforme en español con el mensaje del servicio.
    body = r.json()
    assert body["detail"] == str(exc)


def test_persistencia_no_existe_es_404():
    exc = PersistenciaError("No existe la observación 'obs-1'; no se persistió.")
    r = _app_con(exc).get("/boom")
    assert r.status_code == 404
    assert r.json()["detail"] == str(exc)


def test_persistencia_generica_es_422():
    exc = PersistenciaError("No se pudo persistir la clasificación.")
    r = _app_con(exc).get("/boom")
    assert r.status_code == 422
    assert r.json()["detail"] == str(exc)


# ---------------------------------------------------------------------------
# 503 · Fallo del LLM / proveedor de IA
# ---------------------------------------------------------------------------
def test_bitacora_llm_error_es_503_con_mensaje_del_servicio():
    # ``BitacoraLlmError`` lleva un mensaje en español seguro redactado por el
    # servicio: se expone tal cual (ya está sanitizado en la Capa 2).
    exc = BitacoraLlmError(
        "El asistente no pudo generar la bitácora. Intente nuevamente."
    )
    r = _app_con(exc).get("/boom")
    assert r.status_code == 503
    assert r.json()["detail"] == str(exc)


@pytest.mark.parametrize(
    "exc_factory",
    [LlmError, TranscriptionError, EmbeddingError, ProviderError],
)
def test_error_crudo_de_proveedor_es_503_y_no_filtra_detalles(exc_factory, caplog):
    # Un error crudo de proveedor/AWS que llega sin traducir debe sanitizarse:
    # 503 + mensaje genérico en español; el detalle real NO viaja al cliente.
    exc = exc_factory(_DETALLE_SENSIBLE)
    client = _app_con(exc)
    with caplog.at_level(logging.ERROR, logger="jaimes.api.errors"):
        r = client.get("/boom")

    assert r.status_code == 503
    detalle = r.json()["detail"]

    # No se expone ningún fragmento sensible del error original.
    assert _DETALLE_SENSIBLE not in detalle
    assert "boto3" not in detalle
    assert "arn:aws" not in detalle
    assert "secret-token" not in detalle
    assert "XYZ" not in detalle
    # Mensaje genérico en español orientado al usuario.
    assert "inteligencia artificial" in detalle.lower()

    # El detalle real sí queda registrado para CloudWatch (Requirement 10.6).
    assert any(_DETALLE_SENSIBLE in rec.getMessage() for rec in caplog.records)


def test_cuerpo_de_error_es_uniforme_solo_detail():
    # Todos los errores comparten la misma forma de cuerpo: solo ``detail``.
    r = _app_con(BitacoraSinEvidenciaError("Sin evidencia.")).get("/boom")
    assert set(r.json().keys()) == {"detail"}
