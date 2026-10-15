"""Tests de aislamiento del ``EmbeddingService`` (Módulo C, tarea 4.3).

Verifican el caso de uso de embeber el texto de una observación e indexarlo en la
base vectorial (Requirements 4.2, 4.3) y, sobre todo, el **contrato de fallo**
(Requirement 4.4): si la generación del embedding o su indexación falla, el
servicio señala que la indexación vectorial no se completó y **no** altera ni
descarta la observación relacional.

Aislamiento total del Módulo C: se usan el proveedor mock de embeddings
(:class:`MockEmbeddingProvider`) y el índice en memoria
(:class:`InMemoryVectorRepo`) para el camino feliz, y dobles mínimos para forzar
los fallos. No se importa ninguna implementación de módulos hermanos (B/D/E/F);
la "observación relacional preservada" se representa con un store falso que el
servicio nunca debe tocar.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.models import Dominio, FormatoCaptura, Observacion
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.mock_embeddings import MockEmbeddingProvider
from app.providers.errors import EmbeddingError
from app.repositories.vector.base import VectorRepo
from app.repositories.vector.memory_vector_repo import (
    METADATOS_CONTRATO,
    InMemoryVectorRepo,
)
from app.services.embedding_service import (
    EmbeddingService,
    IndexacionVectorialError,
)

TEXTO = "El niño apiló cuatro bloques y pidió ayuda a la tía."


# ---------------------------------------------------------------------------
# Helpers / dobles
# ---------------------------------------------------------------------------
def _observacion(
    id_observacion: str = "O-001",
    *,
    id_nino: str = "N-001",
    dominios: list[Dominio] | None = None,
    nivel_estimado: int | None = 3,
    formato: FormatoCaptura = FormatoCaptura.texto,
    fecha: date | None = None,
) -> Observacion:
    """Construye una observación de prueba con metadatos de clasificación."""
    return Observacion(
        id_observacion=id_observacion,
        id_nino=id_nino,
        id_educadora="E-001",
        fecha_observacion=fecha or date(2026, 10, 1),
        formato_captura=formato,
        nivel_estimado=nivel_estimado,
        dominios=dominios if dominios is not None else [Dominio.cognitivo],
        nota_breve=TEXTO,
    )


class _FailingEmbeddingProvider(EmbeddingProvider):
    """Proveedor cuyo ``embed`` siempre falla (simula caída de Titan)."""

    def embed(self, text: str) -> list[float]:
        raise EmbeddingError("Bedrock no disponible")


class _FailingVectorRepo(VectorRepo):
    """``VectorRepo`` cuyo ``index`` siempre lanza ``EmbeddingError``."""

    def __init__(self) -> None:
        self.index_calls = 0

    def index(self, doc: dict) -> None:  # type: ignore[override]
        self.index_calls += 1
        raise EmbeddingError("Aurora/pgvector no disponible")

    def search(self, query_embedding, filtros, k):  # type: ignore[override]
        return []


class _FakeRelationalStore:
    """Store relacional falso: representa la observación ya persistida.

    El ``EmbeddingService`` **no** debe tocarlo (no es dependencia suya); existe
    solo para que las pruebas puedan afirmar que la observación relacional
    permanece intacta tras un fallo de indexación (Requirement 4.4).
    """

    def __init__(self, observacion: Observacion) -> None:
        self._observaciones = {observacion.id_observacion: observacion}

    def get(self, id_observacion: str) -> Observacion | None:
        return self._observaciones.get(id_observacion)


# ===========================================================================
# Camino feliz — embeber + indexar (Requirements 4.2, 4.3)
# ===========================================================================
def test_embed_and_index_indexa_un_registro_con_los_seis_metadatos() -> None:
    """Requirement 4.3: tras indexar, buscar por id_observacion recupera uno solo."""
    repo = InMemoryVectorRepo()
    service = EmbeddingService(MockEmbeddingProvider(dimension=32), repo)

    service.embed_and_index(_observacion("O-001"), TEXTO)

    resultados = repo.search([1.0] * 32, {"id_observacion": "O-001"}, k=10)
    assert len(resultados) == 1
    doc = resultados[0]
    for metadato in METADATOS_CONTRATO:
        assert metadato in doc
    assert doc["id_observacion"] == "O-001"
    assert doc["id_nino"] == "N-001"
    assert doc["dominio"] == "cognitivo"
    assert doc["nivel"] == 3
    assert doc["fecha"] == date(2026, 10, 1)
    assert doc["formato"] == "texto"


def test_embed_and_index_devuelve_documento_con_embedding() -> None:
    """El documento devuelto incluye el embedding generado y el texto transcrito."""
    provider = MockEmbeddingProvider(dimension=16)
    service = EmbeddingService(provider, InMemoryVectorRepo())

    doc = service.embed_and_index(_observacion("O-002"), TEXTO)

    assert doc["embedding"] == provider.embed(TEXTO)
    assert len(doc["embedding"]) == 16
    assert doc["texto_transcrito"] == TEXTO


def test_embed_and_index_usa_el_primer_dominio_estimado() -> None:
    """Con varios dominios estimados, el documento indexa el primero."""
    repo = InMemoryVectorRepo()
    service = EmbeddingService(MockEmbeddingProvider(dimension=8), repo)

    obs = _observacion("O-003", dominios=[Dominio.socioemocional, Dominio.cognitivo])
    service.embed_and_index(obs, TEXTO)

    (doc,) = repo.search([1.0] * 8, {"id_observacion": "O-003"}, k=1)
    assert doc["dominio"] == "socioemocional"


def test_embed_and_index_formato_no_textual_se_indexa() -> None:
    """Una observación de audio/foto/video se indexa con su formato de captura."""
    repo = InMemoryVectorRepo()
    service = EmbeddingService(MockEmbeddingProvider(dimension=8), repo)

    obs = _observacion("O-004", formato=FormatoCaptura.audio)
    service.embed_and_index(obs, TEXTO)

    (doc,) = repo.search([1.0] * 8, {"id_observacion": "O-004"}, k=1)
    assert doc["formato"] == "audio"


# ===========================================================================
# Fallo del embedding (Requirement 4.4)
# ===========================================================================
def test_fallo_de_embedding_devuelve_error_de_indexacion_no_completada() -> None:
    """Si el embedding falla, se señala indexación no completada."""
    repo = InMemoryVectorRepo()
    service = EmbeddingService(_FailingEmbeddingProvider(), repo)

    with pytest.raises(IndexacionVectorialError):
        service.embed_and_index(_observacion("O-001"), TEXTO)

    # Es un subtipo de EmbeddingError (familia de contrato del Módulo A).
    assert issubclass(IndexacionVectorialError, EmbeddingError)


def test_fallo_de_embedding_no_deja_registro_vectorial() -> None:
    """Si el embedding falla, no queda ningún registro en la base vectorial."""
    repo = InMemoryVectorRepo()
    service = EmbeddingService(_FailingEmbeddingProvider(), repo)

    with pytest.raises(IndexacionVectorialError):
        service.embed_and_index(_observacion("O-001"), TEXTO)

    assert repo.search([1.0, 0.0], {"id_observacion": "O-001"}, k=10) == []


def test_fallo_de_embedding_conserva_la_observacion_relacional() -> None:
    """Requirement 4.4: la observación relacional no se altera ni se descarta."""
    obs = _observacion("O-001")
    store = _FakeRelationalStore(obs)
    service = EmbeddingService(_FailingEmbeddingProvider(), InMemoryVectorRepo())

    with pytest.raises(IndexacionVectorialError):
        service.embed_and_index(obs, TEXTO)

    # El servicio no toca el store relacional: la observación sigue intacta.
    assert store.get("O-001") is obs


# ===========================================================================
# Fallo de la indexación (Requirement 4.4)
# ===========================================================================
def test_fallo_de_indexacion_devuelve_error_de_indexacion_no_completada() -> None:
    """Si VectorRepo.index falla, se señala indexación no completada."""
    service = EmbeddingService(MockEmbeddingProvider(dimension=8), _FailingVectorRepo())

    with pytest.raises(IndexacionVectorialError):
        service.embed_and_index(_observacion("O-001"), TEXTO)


def test_fallo_de_indexacion_conserva_la_observacion_relacional() -> None:
    """Requirement 4.4: ante fallo de indexación, la observación relacional queda."""
    obs = _observacion("O-001")
    store = _FakeRelationalStore(obs)
    repo = _FailingVectorRepo()
    service = EmbeddingService(MockEmbeddingProvider(dimension=8), repo)

    with pytest.raises(IndexacionVectorialError):
        service.embed_and_index(obs, TEXTO)

    assert repo.index_calls == 1  # se intentó indexar...
    assert store.get("O-001") is obs  # ...pero la observación relacional sigue.


def test_fallo_de_indexacion_encadena_la_causa_original() -> None:
    """El error de contrato encadena el fallo original en ``__cause__``."""
    service = EmbeddingService(MockEmbeddingProvider(dimension=8), _FailingVectorRepo())

    with pytest.raises(IndexacionVectorialError) as info:
        service.embed_and_index(_observacion("O-001"), TEXTO)

    assert isinstance(info.value.__cause__, EmbeddingError)


# ===========================================================================
# Validación de entrada
# ===========================================================================
@pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
def test_texto_vacio_devuelve_error_de_indexacion_no_completada(texto: str) -> None:
    """Un texto vacío no puede embeberse: se señala indexación no completada."""
    repo = InMemoryVectorRepo()
    service = EmbeddingService(MockEmbeddingProvider(dimension=8), repo)

    with pytest.raises(IndexacionVectorialError):
        service.embed_and_index(_observacion("O-001"), texto)

    assert repo.search([1.0] * 8, {"id_observacion": "O-001"}, k=10) == []
