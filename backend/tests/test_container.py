"""Tests del contenedor de DI (tarea 9.2 — Módulo G).

Verifican que el contenedor ``Container`` de ``app.core`` selecciona los
adaptadores/repos correctos según ``USE_MOCKS`` y cablea los siete servicios de
la lógica de negocio detrás de sus interfaces (DIP), tanto en el camino mock
(local/CI) como en el camino AWS (producción) — sin hacer ninguna llamada real
a AWS (Requirements 10.3, 10.7, 13.5).

Cobertura:
- Modo mock: construye los 7 servicios con implementaciones mock + repos
  locales (SQLite, índice en memoria, almacenamiento local).
- Modo AWS: selecciona las clases de adaptadores AWS (Transcribe/Textract,
  Titan, Bedrock) + pgvector + S3, sin invocar red (clientes diferidos).
- Intercambiabilidad (LSP): cada servicio recibe la interfaz, con el concreto
  correcto según el modo.
- Singletons cacheados: la misma dependencia se construye una sola vez.
- Las funciones proveedoras de ``Depends(...)`` devuelven los servicios del
  contenedor del proceso.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.container import (
    Container,
    get_bitacora_service,
    get_classification_service,
    get_container,
    get_director_report_service,
    get_embedding_service,
    get_ingestion_service,
    get_recommendation_service,
    get_transcription_service,
    reset_container,
)
from app.providers.classifier.base import Classifier
from app.providers.classifier.bedrock_llm import LlmClassifier
from app.providers.classifier.rule_based import RuleBasedClassifier
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.mock_embeddings import MockEmbeddingProvider
from app.providers.embeddings.titan_embeddings import TitanEmbeddingProvider
from app.providers.llm.base import LlmProvider
from app.providers.llm.bedrock_llm import BedrockLlmProvider
from app.providers.llm.guarded_llm import GuardedLlmProvider
from app.providers.llm.mock_llm import MockLlmProvider
from app.providers.transcription.aws_transcription import AwsTranscriptionProvider
from app.providers.transcription.base import TranscriptionProvider
from app.providers.transcription.mock_transcription import MockTranscriptionProvider
from app.providers.transcription.nova_sonic import NovaSonicTranscriptionProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.relational.sqlalchemy_repo import SqlAlchemyRelationalRepo
from app.repositories.storage.base import StorageRepo
from app.repositories.storage.local_storage import LocalStorageRepo
from app.repositories.storage.s3_storage import S3StorageRepo
from app.repositories.vector.base import VectorRepo
from app.repositories.vector.memory_vector_repo import InMemoryVectorRepo
from app.repositories.vector.pgvector_repo import PgVectorRepo
from app.services.bitacora_service import BitacoraService
from app.services.classification_service import ClassificationService
from app.services.director_report_service import DirectorReportService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.recommendation_service import RecommendationService
from app.services.transcription_service import TranscriptionService


# ---------------------------------------------------------------------------
# Helpers de configuración (sin tocar el entorno real)
# ---------------------------------------------------------------------------
def _mock_settings() -> Settings:
    """Config de modo demo: adaptadores mock + SQLite en memoria."""
    return Settings(
        _env_file=None,
        environment="development",
        database_url="sqlite://",
        local_storage_dir="./.pytest_storage",
    )


def _aws_settings() -> Settings:
    """Config de modo AWS con IA real habilitada, sin llamadas de red."""
    return Settings(
        _env_file=None,
        environment="production",
        ai_enabled=True,
        database_url="sqlite://",
        aws_region="us-east-1",
        s3_bucket="jaimes-test",
    )


# ---------------------------------------------------------------------------
# Modo mock (local/CI)
# ---------------------------------------------------------------------------
def test_mock_mode_selecciona_adaptadores_y_repos_mock() -> None:
    c = Container(_mock_settings())

    assert isinstance(c.transcription_provider, TranscriptionProvider)
    assert isinstance(c.transcription_provider, MockTranscriptionProvider)

    assert isinstance(c.embedding_provider, EmbeddingProvider)
    assert isinstance(c.embedding_provider, MockEmbeddingProvider)

    assert isinstance(c.llm_provider, LlmProvider)
    # El LLM se expone envuelto por el resguardo de datos sensibles
    # (despersonalización, Requirements 11.2, 11.3), que a su vez envuelve el
    # adaptador mock seleccionado por ``USE_MOCKS``.
    assert isinstance(c.llm_provider, GuardedLlmProvider)
    assert isinstance(c.llm_provider._inner, MockLlmProvider)

    assert isinstance(c.classifier, Classifier)
    assert isinstance(c.classifier, RuleBasedClassifier)

    assert isinstance(c.relational_repo, RelationalRepo)
    assert isinstance(c.relational_repo, SqlAlchemyRelationalRepo)

    assert isinstance(c.vector_repo, VectorRepo)
    assert isinstance(c.vector_repo, InMemoryVectorRepo)

    assert isinstance(c.storage_repo, StorageRepo)
    assert isinstance(c.storage_repo, LocalStorageRepo)


def test_mock_mode_construye_los_siete_servicios() -> None:
    c = Container(_mock_settings())

    assert isinstance(c.transcription_service, TranscriptionService)
    assert isinstance(c.embedding_service, EmbeddingService)
    assert isinstance(c.classification_service, ClassificationService)
    assert isinstance(c.ingestion_service, IngestionService)
    assert isinstance(c.bitacora_service, BitacoraService)
    assert isinstance(c.recommendation_service, RecommendationService)
    assert isinstance(c.director_report_service, DirectorReportService)


def test_servicios_comparten_las_mismas_dependencias_cacheadas() -> None:
    c = Container(_mock_settings())

    # Misma instancia en accesos repetidos (singletons por contenedor).
    assert c.vector_repo is c.vector_repo
    assert c.relational_repo is c.relational_repo
    assert c.llm_provider is c.llm_provider
    assert c.embedding_service is c.embedding_service

    # El servicio de bitácora y el de recomendación comparten el mismo repo y
    # el mismo índice vectorial del contenedor (grafo coherente).
    assert c.bitacora_service._repo is c.relational_repo
    assert c.recommendation_service._vector is c.vector_repo
    assert c.ingestion_service._repo is c.relational_repo


def test_ingestion_embedding_adapter_indexa_via_embedding_service() -> None:
    """La ingesta recibe un puerto con ``index_observacion`` que delega en C."""
    c = Container(_mock_settings())
    puerto = c.ingestion_service._embeddings
    assert hasattr(puerto, "index_observacion")


# ---------------------------------------------------------------------------
# Modo AWS (producción) — selección de clases, sin red
# ---------------------------------------------------------------------------
def test_aws_mode_selecciona_adaptadores_aws() -> None:
    c = Container(_aws_settings())

    assert isinstance(c.transcription_provider, NovaSonicTranscriptionProvider)
    assert isinstance(c.transcription_provider, TranscriptionProvider)

    assert isinstance(c.vector_repo, PgVectorRepo)
    assert isinstance(c.vector_repo, VectorRepo)


def test_aws_mode_providers_bedrock_son_diferidos() -> None:
    """Los adaptadores AWS que requieren boto3 se seleccionan sin invocar red."""
    c = Container(_aws_settings())

    assert isinstance(c.embedding_provider, TitanEmbeddingProvider)
    # El LLM AWS (Bedrock) se expone envuelto por el resguardo de datos
    # sensibles (Requirements 11.2, 11.3).
    assert isinstance(c.llm_provider, GuardedLlmProvider)
    assert isinstance(c.llm_provider._inner, BedrockLlmProvider)
    # El clasificador primario es el LLM, cableado sobre el LlmProvider AWS.
    assert isinstance(c.classifier, LlmClassifier)


def test_aws_mode_storage_es_s3() -> None:
    c = Container(_aws_settings())
    # Construir el adaptador S3 no debe requerir red (solo crea el cliente).
    assert isinstance(c.storage_repo, S3StorageRepo)
    assert isinstance(c.storage_repo, StorageRepo)


def test_aws_mode_construye_los_siete_servicios() -> None:
    c = Container(_aws_settings())
    assert isinstance(c.transcription_service, TranscriptionService)
    assert isinstance(c.embedding_service, EmbeddingService)
    assert isinstance(c.classification_service, ClassificationService)
    assert isinstance(c.ingestion_service, IngestionService)
    assert isinstance(c.bitacora_service, BitacoraService)
    assert isinstance(c.recommendation_service, RecommendationService)
    assert isinstance(c.director_report_service, DirectorReportService)


# ---------------------------------------------------------------------------
# Integración con FastAPI (Depends) — contenedor del proceso
# ---------------------------------------------------------------------------
def test_proveedores_depends_devuelven_servicios_del_contenedor() -> None:
    reset_container()
    try:
        contenedor = get_container()
        assert get_transcription_service() is contenedor.transcription_service
        assert get_embedding_service() is contenedor.embedding_service
        assert get_classification_service() is contenedor.classification_service
        assert get_ingestion_service() is contenedor.ingestion_service
        assert get_bitacora_service() is contenedor.bitacora_service
        assert get_recommendation_service() is contenedor.recommendation_service
        assert (
            get_director_report_service() is contenedor.director_report_service
        )
    finally:
        reset_container()


def test_reset_container_crea_una_instancia_nueva() -> None:
    reset_container()
    primero = get_container()
    reset_container()
    segundo = get_container()
    assert primero is not segundo
    reset_container()


def test_local_con_api_key_usa_bedrock_sin_cambiar_repos_locales() -> None:
    settings = Settings(
        environment="development",
        database_url="sqlite://",
        bedrock_api_key="clave-de-prueba",
    )
    container = Container(settings)

    assert isinstance(container.llm_provider, GuardedLlmProvider)
    assert isinstance(container.llm_provider._inner, BedrockLlmProvider)
    assert isinstance(
        container.transcription_provider, NovaSonicTranscriptionProvider
    )
    assert isinstance(container.vector_repo, InMemoryVectorRepo)
    assert isinstance(container.storage_repo, LocalStorageRepo)


def test_ai_enabled_usa_bedrock_y_nova_con_repos_locales() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        ai_enabled=True,
        database_url="sqlite://",
        local_storage_dir="./.pytest_storage",
    )
    container = Container(settings)

    assert isinstance(container.relational_repo, SqlAlchemyRelationalRepo)
    assert isinstance(container.vector_repo, InMemoryVectorRepo)
    assert isinstance(container.storage_repo, LocalStorageRepo)
    assert isinstance(container.embedding_provider, MockEmbeddingProvider)
    assert isinstance(container.llm_provider._inner, BedrockLlmProvider)
    assert isinstance(container.classifier, LlmClassifier)
    assert isinstance(
        container.transcription_provider, NovaSonicTranscriptionProvider
    )
    assert container.transcription_provider._api_key == ""
