"""Tests de los adaptadores de ``EmbeddingProvider`` (Módulo C, tarea 4.1).

Cubren el adaptador mock (determinismo, dimensión, intercambiabilidad) y el
adaptador Titan (invocación de Bedrock con un cliente boto3 simulado, traducción
de errores a ``EmbeddingError``). Trazabilidad: Requirements 4.2, 4.5.

El adaptador Titan recibe el cliente ``bedrock-runtime`` por inyección (DIP), de
modo que las pruebas usan un doble en memoria sin red ni credenciales AWS.
"""

from __future__ import annotations

import io
import json

import pytest

from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.mock_embeddings import (
    DEFAULT_DIMENSION,
    MockEmbeddingProvider,
)
from app.providers.embeddings.titan_embeddings import TitanEmbeddingProvider
from app.providers.errors import EmbeddingError


# ---------------------------------------------------------------------------
# Adaptador mock
# ---------------------------------------------------------------------------
def test_mock_es_embedding_provider() -> None:
    """El mock implementa la interfaz congelada del Módulo A."""
    assert isinstance(MockEmbeddingProvider(), EmbeddingProvider)


def test_mock_dimension_por_defecto_coincide_con_titan() -> None:
    """La dimensión por defecto coincide con Titan v2 (intercambiabilidad)."""
    provider = MockEmbeddingProvider()
    vector = provider.embed("una observación de ejemplo")
    assert len(vector) == DEFAULT_DIMENSION == 1024


def test_mock_dimension_personalizada() -> None:
    """La dimensión configurada se respeta en la salida."""
    provider = MockEmbeddingProvider(dimension=256)
    assert len(provider.embed("texto")) == 256


def test_mock_es_determinista() -> None:
    """Requirement 4.5: mismo texto ⇒ mismo vector (reproducibilidad)."""
    provider = MockEmbeddingProvider()
    texto = "El niño apiló cuatro bloques y pidió ayuda a la tía."
    assert provider.embed(texto) == provider.embed(texto)


def test_mock_determinista_entre_instancias() -> None:
    """El determinismo no depende de la instancia ni del proceso."""
    a = MockEmbeddingProvider(dimension=128)
    b = MockEmbeddingProvider(dimension=128)
    assert a.embed("misma entrada") == b.embed("misma entrada")


def test_mock_textos_distintos_dan_vectores_distintos() -> None:
    """Textos diferentes producen embeddings diferentes."""
    provider = MockEmbeddingProvider()
    assert provider.embed("primero") != provider.embed("segundo")


def test_mock_vector_normalizado_l2() -> None:
    """El vector mock está normalizado a norma unitaria (coseno = producto punto)."""
    provider = MockEmbeddingProvider(dimension=64)
    vector = provider.embed("texto a normalizar")
    norma = sum(c * c for c in vector) ** 0.5
    assert norma == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
def test_mock_texto_vacio_lanza_embedding_error(texto: str) -> None:
    """Requirement 4.4: texto vacío lanza ``EmbeddingError``."""
    with pytest.raises(EmbeddingError):
        MockEmbeddingProvider().embed(texto)


def test_mock_dimension_invalida() -> None:
    """Una dimensión no positiva es rechazada en construcción."""
    with pytest.raises(ValueError):
        MockEmbeddingProvider(dimension=0)


# ---------------------------------------------------------------------------
# Adaptador Titan (Bedrock) — cliente boto3 simulado
# ---------------------------------------------------------------------------
class _FakeBedrockClient:
    """Doble del cliente ``bedrock-runtime`` que devuelve un embedding fijo."""

    def __init__(self, embedding: list[float], as_stream: bool = True) -> None:
        self._embedding = embedding
        self._as_stream = as_stream
        self.last_call: dict | None = None

    def invoke_model(self, **kwargs: object) -> dict:
        self.last_call = dict(kwargs)
        payload = json.dumps({"embedding": self._embedding}).encode("utf-8")
        body: object = io.BytesIO(payload) if self._as_stream else payload
        return {"body": body}


class _FailingBedrockClient:
    """Doble que simula un fallo del SDK (p. ej. ClientError)."""

    def invoke_model(self, **kwargs: object) -> dict:
        raise RuntimeError("Bedrock no disponible")


def test_titan_es_embedding_provider() -> None:
    """El adaptador Titan implementa la interfaz congelada del Módulo A."""
    provider = TitanEmbeddingProvider(client=_FakeBedrockClient([0.1, 0.2]))
    assert isinstance(provider, EmbeddingProvider)


def test_titan_devuelve_el_embedding_de_la_respuesta() -> None:
    """El adaptador decodifica el ``body`` y devuelve el vector como floats."""
    esperado = [0.1, 0.2, 0.3, 0.4]
    client = _FakeBedrockClient(esperado)
    provider = TitanEmbeddingProvider(client=client, model_id="amazon.titan-embed-text-v2:0")

    vector = provider.embed("texto de observación")

    assert vector == esperado
    assert all(isinstance(c, float) for c in vector)


def test_titan_invoca_bedrock_con_el_cuerpo_esperado() -> None:
    """Verifica modelId y el cuerpo JSON (inputText/dimensions/normalize)."""
    client = _FakeBedrockClient([1.0])
    provider = TitanEmbeddingProvider(
        client=client,
        model_id="amazon.titan-embed-text-v2:0",
        dimensions=512,
        normalize=True,
    )

    provider.embed("hola")

    assert client.last_call is not None
    assert client.last_call["modelId"] == "amazon.titan-embed-text-v2:0"
    body = json.loads(client.last_call["body"])
    assert body == {"inputText": "hola", "dimensions": 512, "normalize": True}


def test_titan_acepta_body_bytes_sin_stream() -> None:
    """La respuesta funciona tanto con StreamingBody como con bytes."""
    client = _FakeBedrockClient([0.5, 0.6], as_stream=False)
    provider = TitanEmbeddingProvider(client=client)
    assert provider.embed("texto") == [0.5, 0.6]


@pytest.mark.parametrize("texto", ["", "   "])
def test_titan_texto_vacio_lanza_embedding_error(texto: str) -> None:
    """Requirement 4.4: texto vacío no invoca a Bedrock y lanza error."""
    client = _FakeBedrockClient([0.1])
    with pytest.raises(EmbeddingError):
        TitanEmbeddingProvider(client=client).embed(texto)
    assert client.last_call is None


def test_titan_traduce_fallo_del_sdk_a_embedding_error() -> None:
    """Cualquier excepción del SDK se traduce a ``EmbeddingError`` (Req. 4.4)."""
    provider = TitanEmbeddingProvider(client=_FailingBedrockClient())
    with pytest.raises(EmbeddingError):
        provider.embed("texto")


def test_titan_respuesta_sin_embedding_lanza_error() -> None:
    """Una respuesta sin vector válido se traduce a ``EmbeddingError``."""

    class _SinEmbedding:
        def invoke_model(self, **kwargs: object) -> dict:
            return {"body": json.dumps({"embedding": []}).encode("utf-8")}

    provider = TitanEmbeddingProvider(client=_SinEmbedding())
    with pytest.raises(EmbeddingError):
        provider.embed("texto")


# ---------------------------------------------------------------------------
# Intercambiabilidad (LSP) — mismo contrato observable
# ---------------------------------------------------------------------------
def test_adaptadores_son_intercambiables() -> None:
    """Mock y Titan exponen el mismo contrato ``embed(text) -> list[float]``."""
    titan = TitanEmbeddingProvider(client=_FakeBedrockClient([0.1, 0.2, 0.3]))
    mock = MockEmbeddingProvider(dimension=3)

    for provider in (titan, mock):
        vector = provider.embed("texto")
        assert isinstance(vector, list)
        assert all(isinstance(c, float) for c in vector)
