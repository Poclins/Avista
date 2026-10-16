"""Contenedor de inyección de dependencias (DI) de jAImes (Capa 2, Módulo G).

Este contenedor es el **único** punto donde se eligen implementaciones
concretas. Lee la configuración (``Settings``, en particular ``USE_MOCKS``) y
construye los adaptadores de providers y los repositorios detrás de sus
interfaces congeladas (Módulo A), para luego cablear los servicios de la lógica
de negocio (DIP: los servicios solo ven interfaces, nunca ``boto3`` ni
SQLAlchemy directamente).

Selección por ``USE_MOCKS`` (Requirements 10.3, 10.7, 13.5):

- ``USE_MOCKS=true`` (local/CI): adaptadores mock (transcripción, embeddings,
  LLM) + clasificador basado en reglas, repositorio relacional SQLite,
  índice vectorial en memoria y almacenamiento local.
- ``USE_MOCKS=false`` (AWS, camino primario): adaptadores AWS
  (Transcribe/Textract/Rekognition, Titan, Bedrock Claude) + clasificador LLM,
  repositorio relacional Postgres/Aurora, pgvector sobre Aurora y S3.

El **mismo** contenedor sirve en AWS Lambda (producción, FastAPI envuelto por
Mangum) y en ``uvicorn`` local: la diferencia la marca únicamente la
configuración, no el código. Los routers (tarea 9.3) reciben los servicios con
``Depends(...)`` apuntando a las funciones proveedoras de este módulo
(Requirement 10.7).

Diseño: las dependencias se construyen de forma **perezosa** y se **cachean**
por contenedor (una instancia por proceso), de modo que importar o instanciar el
contenedor no exige red ni credenciales; los clientes ``boto3`` y el engine SQL
solo se crean cuando un servicio los necesita realmente.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

from app.core.config import Settings, get_settings
from app.domain.models import Dominio as DominioDominio
from app.domain.models import Manifestacion as ManifestacionDominio
from app.providers.classifier import build_classifier
from app.providers.classifier.base import Classifier
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.mock_embeddings import MockEmbeddingProvider
from app.providers.embeddings.titan_embeddings import (
    DEFAULT_DIMENSION as _TITAN_DIM,
)
from app.providers.embeddings.titan_embeddings import TitanEmbeddingProvider
from app.providers.llm.base import LlmProvider
from app.providers.llm.bedrock_llm import BedrockLlmProvider
from app.providers.llm.guarded_llm import GuardedLlmProvider
from app.providers.llm.mock_llm import MockLlmProvider
from app.providers.transcription.aws_transcription import AwsTranscriptionProvider
from app.providers.transcription.base import TranscriptionProvider
from app.providers.transcription.mock_transcription import MockTranscriptionProvider
from app.providers.transcription.nova_sonic import NovaSonicTranscriptionProvider
from app.repositories.db import create_db_engine, create_session_factory
from app.repositories.relational.base import RelationalRepo
from app.repositories.relational.sqlalchemy_repo import SqlAlchemyRelationalRepo
from app.repositories.schema import Manifestacion as ManifestacionORM
from app.repositories.schema import Observacion as ObservacionORM
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


class _IngestionEmbeddingAdapter:
    """Adapta el ``EmbeddingService`` (Módulo C) al puerto que usa la ingesta.

    El ``IngestionService`` (Módulo D) consume un puerto mínimo con la capacidad
    ``index_observacion(id_observacion, texto)``, mientras que el
    ``EmbeddingService`` del Módulo C expone ``embed_and_index(observacion,
    texto)`` sobre la entidad de dominio. Este adaptador resuelve el desfase sin
    acoplar los módulos: recupera la observación persistida vía ``RelationalRepo``
    (interfaz), la convierte a la entidad de dominio y delega en el servicio de
    embeddings. Un fallo de indexación no debe deshacer la observación relacional
    ya creada (Requirement 4.4): el ``EmbeddingService`` ya respeta ese contrato.
    """

    def __init__(self, embeddings: EmbeddingService, repo: RelationalRepo) -> None:
        self._embeddings = embeddings
        self._repo = repo

    def index_observacion(self, id_observacion: str, texto: str) -> None:
        obs_orm = self._repo.get(ObservacionORM, id_observacion)
        if obs_orm is None:  # pragma: no cover - inconsistencia improbable
            return
        try:
            manifestaciones = self._repo.manifestaciones_de_observacion(
                id_observacion
            )
        except (AttributeError, NotImplementedError):
            manifestaciones = []
        observacion = _orm_a_observacion_dominio(obs_orm, manifestaciones)
        self._embeddings.embed_and_index(observacion, texto)


def _orm_a_observacion_dominio(
    obs: ObservacionORM,
    manifestaciones: list[Any] | None = None,
) -> Any:
    """Convierte una observación ORM separada de la sesión al dominio.

    Las manifestaciones se reciben desde una consulta explícita del repositorio;
    nunca se activa la relación lazy de una entidad detached.
    """
    from app.domain.models import Observacion as ObservacionDominio

    dominios: list[DominioDominio] = []
    for manifestacion in manifestaciones or []:
        dominio = getattr(manifestacion, "dominio", None)
        if dominio is not None and dominio not in dominios:
            dominios.append(dominio)

    return ObservacionDominio(
        id_observacion=obs.id_observacion,
        id_nino=obs.id_nino,
        id_educadora=obs.id_educadora,
        fecha_observacion=obs.fecha_observacion,
        formato_captura=obs.formato_captura,
        nivel_estimado=obs.nivel_estimado,
        dominios=dominios,
        nota_breve=obs.nota_breve or "",
    )


class Container:
    """Contenedor de DI: construye providers, repos y servicios según la config.

    Una instancia representa el grafo de dependencias de un proceso. Cada
    dependencia se construye una sola vez (``cached_property``) y se reutiliza,
    de modo que todos los servicios compartan los mismos repositorios y
    adaptadores (p. ej. el índice vectorial en memoria en modo mock).

    Args:
        settings: configuración activa; por defecto, la instancia cacheada de
            :func:`app.core.config.get_settings`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def use_mocks(self) -> bool:
        return self._settings.use_mocks

    # ------------------------------------------------------------------
    # Infraestructura relacional (engine + sesión)
    # ------------------------------------------------------------------
    @cached_property
    def _database_url(self) -> str:
        """URL de BD efectiva, resuelta de forma perezosa (una vez por proceso).

        En modo mock es la ``database_url`` por defecto (SQLite); en el camino
        AWS se arma desde el secreto de Aurora (Secrets Manager) + los datos de
        conexión inyectados por ``ComputeStack`` (ver
        :meth:`Settings.resolve_database_url`). Se cachea para no releer el
        secreto en cada acceso.
        """
        return self._settings.resolve_database_url()

    @cached_property
    def _session_factory(self) -> Any:
        engine = create_db_engine(self._database_url)
        return create_session_factory(engine)

    # ------------------------------------------------------------------
    # Repositorios (Capa 3) — selección por USE_MOCKS
    # ------------------------------------------------------------------
    @cached_property
    def relational_repo(self) -> RelationalRepo:
        """Repositorio relacional (SQLite en mock, Postgres/Aurora en AWS).

        Ambos caminos usan la misma implementación ``SqlAlchemyRelationalRepo``;
        la ``database_url`` de la configuración decide el motor (SQLite vs
        Postgres), manteniendo intercambiabilidad (LSP).
        """
        return SqlAlchemyRelationalRepo(self._session_factory)

    @cached_property
    def vector_repo(self) -> VectorRepo:
        """Repositorio vectorial: índice en memoria (mock) o pgvector (AWS)."""
        if self.use_mocks:
            return InMemoryVectorRepo()
        # La dimensión debe coincidir con la del EmbeddingProvider (Titan v2).
        return PgVectorRepo(self._pg_connection_factory, dim=_TITAN_DIM)

    @cached_property
    def storage_repo(self) -> StorageRepo:
        """Almacenamiento de medios: local (mock) o S3 cifrado (AWS)."""
        if self.use_mocks:
            return LocalStorageRepo(self._settings.local_storage_dir)
        return S3StorageRepo(
            bucket=self._settings.s3_bucket,
            client=self._boto3_client("s3"),
            prefix="observaciones",
        )

    # ------------------------------------------------------------------
    # Providers de IA (Capa 2) — selección por USE_MOCKS
    # ------------------------------------------------------------------
    @cached_property
    def transcription_provider(self) -> TranscriptionProvider:
        """Audio usa Nova Sonic cuando existe una API key Bedrock."""
        sonic_key = self._settings.nova_sonic_api_key_value
        if sonic_key:
            return NovaSonicTranscriptionProvider(
                api_key=sonic_key,
                region=self._settings.aws_region,
                model_id=self._settings.nova_sonic_model_id,
                storage_dir=self._settings.local_storage_dir,
                max_seconds=self._settings.nova_sonic_max_seconds,
            )
        if self.use_mocks:
            return MockTranscriptionProvider()
        return AwsTranscriptionProvider(region=self._settings.aws_region)

    @cached_property
    def embedding_provider(self) -> EmbeddingProvider:
        """Embeddings: mock determinista (local) o Amazon Titan (AWS)."""
        if self.use_mocks:
            return MockEmbeddingProvider()
        return TitanEmbeddingProvider(
            client=self._boto3_client("bedrock-runtime"),
            model_id=self._settings.titan_embedding_model_id,
        )

    @cached_property
    def llm_provider(self) -> LlmProvider:
        """LLM: mock (local) o Amazon Bedrock (Claude) (AWS).

        El proveedor activo se **envuelve** con ``GuardedLlmProvider`` para
        aplicar el resguardo de datos sensibles (despersonalización) en el único
        punto de cableado del LLM: así todos los servicios que generan texto
        (bitácora, recomendación, reporte) quedan protegidos sin duplicar la
        validación (Requirements 11.2, 11.3).
        """
        if self._settings.use_bedrock:
            inner: LlmProvider = BedrockLlmProvider(
                region=self._settings.aws_region,
                model_id=self._settings.bedrock_model_id,
                api_key=self._settings.bedrock_api_key_value,
            )
        else:
            inner = MockLlmProvider()
        return GuardedLlmProvider(inner)

    @cached_property
    def classifier(self) -> Classifier:
        """Clasificador: reglas (local) o LLM (AWS), con catálogo del dataset E-1.

        El catálogo de manifestaciones se carga desde el repositorio relacional
        (dataset E-1 sembrado) y se mapea al dominio del Módulo A; el camino
        primario reutiliza el ``LlmProvider`` activo.
        """
        usar_llm = self._settings.use_bedrock
        return build_classifier(
            self._catalogo_manifestaciones(),
            use_mocks=not usar_llm,
            llm=self.llm_provider if usar_llm else None,
        )

    # ------------------------------------------------------------------
    # Servicios (Capa 2) — cableados solo con interfaces (DIP)
    # ------------------------------------------------------------------
    @cached_property
    def transcription_service(self) -> TranscriptionService:
        return TranscriptionService(self.transcription_provider)

    @cached_property
    def embedding_service(self) -> EmbeddingService:
        return EmbeddingService(self.embedding_provider, self.vector_repo)

    @cached_property
    def classification_service(self) -> ClassificationService:
        return ClassificationService(self.classifier, self.relational_repo)

    @cached_property
    def ingestion_service(self) -> IngestionService:
        return IngestionService(
            storage=self.storage_repo,
            transcriber=self.transcription_provider,
            classifier=self.classifier,
            repo=self.relational_repo,
            embeddings=_IngestionEmbeddingAdapter(
                self.embedding_service, self.relational_repo
            ),
        )

    @cached_property
    def bitacora_service(self) -> BitacoraService:
        return BitacoraService(
            repo=self.relational_repo,
            vector=self.vector_repo,
            llm=self.llm_provider,
            embeddings=self.embedding_provider,
        )

    @cached_property
    def recommendation_service(self) -> RecommendationService:
        return RecommendationService(
            repo=self.relational_repo,
            vector_repo=self.vector_repo,
            llm=self.llm_provider,
            embeddings=self.embedding_provider,
        )

    @cached_property
    def director_report_service(self) -> DirectorReportService:
        return DirectorReportService(
            repo=self.relational_repo,
            llm=self.llm_provider,
        )

    # ------------------------------------------------------------------
    # Helpers internos (camino AWS / carga de catálogo)
    # ------------------------------------------------------------------
    def _catalogo_manifestaciones(self) -> list[ManifestacionDominio]:
        """Carga el catálogo de manifestaciones (dominio) desde el repo relacional.

        Si la base aún no está sembrada (o no es accesible), devuelve una lista
        vacía: el clasificador sigue siendo construible y marcará las
        observaciones como pendientes de clasificación manual hasta que haya
        catálogo, sin romper el arranque del contenedor.
        """
        try:
            filas = self.relational_repo.list(ManifestacionORM)
        except Exception:  # noqa: BLE001 - base no sembrada/accesible al construir
            return []
        return [
            ManifestacionDominio(
                id_manifestacion=m.id_manifestacion,
                nivel=m.nivel,
                dominio=m.dominio,
                texto_observable=m.texto_observable,
            )
            for m in filas
        ]

    @cached_property
    def _pg_connection_factory(self) -> Any:
        """Factoría de conexiones psycopg para pgvector (solo camino AWS).

        Devuelve un callable sin argumentos que abre una conexión nueva a partir
        de la ``database_url`` de la configuración. Se construye de forma
        perezosa para no exigir ``psycopg`` ni red en modo mock.
        """
        import psycopg  # import diferido: solo en el camino AWS/Postgres.

        # ``_database_url`` es una URL SQLAlchemy (``postgresql+psycopg://``);
        # ``psycopg.connect`` espera una URL libpq (``postgresql://``), así que
        # se normaliza el prefijo del dialecto.
        url = self._database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )

        def _factory() -> Any:
            return psycopg.connect(url)

        return _factory

    def _boto3_client(self, servicio: str) -> Any:
        """Crea un cliente boto3 para el servicio dado (solo camino AWS).

        Import diferido: ``boto3`` solo se necesita cuando ``USE_MOCKS=false``.
        """
        import boto3  # import diferido: solo en el camino AWS.

        return boto3.client(servicio, region_name=self._settings.aws_region)


# ---------------------------------------------------------------------------
# Integración con FastAPI (Depends) — Requirement 10.7
# ---------------------------------------------------------------------------
# Un único contenedor por proceso: en Lambda (Mangum) y en uvicorn local el
# contenedor se construye una vez y se reutiliza en todas las peticiones, con la
# misma configuración. Los routers (tarea 9.3) declaran sus dependencias con
# ``Depends(get_<servicio>)``.
_container: Container | None = None


def get_container() -> Container:
    """Devuelve el contenedor de DI del proceso (lo crea en el primer uso)."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """Reinicia el contenedor del proceso (útil en pruebas que cambian config)."""
    global _container
    _container = None


# -- Funciones proveedoras para ``Depends(...)`` ----------------------------
def get_transcription_service() -> TranscriptionService:
    """Proveedor FastAPI del ``TranscriptionService``."""
    return get_container().transcription_service


def get_embedding_service() -> EmbeddingService:
    """Proveedor FastAPI del ``EmbeddingService``."""
    return get_container().embedding_service


def get_classification_service() -> ClassificationService:
    """Proveedor FastAPI del ``ClassificationService``."""
    return get_container().classification_service


def get_ingestion_service() -> IngestionService:
    """Proveedor FastAPI del ``IngestionService``."""
    return get_container().ingestion_service


def get_bitacora_service() -> BitacoraService:
    """Proveedor FastAPI del ``BitacoraService``."""
    return get_container().bitacora_service


def get_recommendation_service() -> RecommendationService:
    """Proveedor FastAPI del ``RecommendationService``."""
    return get_container().recommendation_service


def get_director_report_service() -> DirectorReportService:
    """Proveedor FastAPI del ``DirectorReportService``."""
    return get_container().director_report_service


def get_relational_repo() -> RelationalRepo:
    """Proveedor FastAPI del ``RelationalRepo``.

    Los routers de solo lectura (ficha de niño/a, "Mi sala", listados de
    observaciones/bitácoras/recomendaciones y la ruta de niveles de referencia)
    consultan el repositorio relacional directamente a través de su interfaz
    congelada (Módulo A), sin crear un servicio adicional para operaciones que
    son lecturas puras. Mantiene el DIP: el router ve solo la abstracción.
    """
    return get_container().relational_repo


__all__ = [
    "Container",
    "get_container",
    "reset_container",
    "get_transcription_service",
    "get_embedding_service",
    "get_classification_service",
    "get_ingestion_service",
    "get_bitacora_service",
    "get_recommendation_service",
    "get_director_report_service",
    "get_relational_repo",
]
