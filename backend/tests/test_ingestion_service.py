"""Tests del ``IngestionService`` (tarea 5.4 — Módulo D).

Verifican la orquestación idempotente de la ingesta de observaciones usando
**solo fakes locales** de los puertos (aislamiento del Módulo D, Requirement
13): no se importan implementaciones concretas de módulos hermanos (ni el
``Classifier`` real del Módulo E ni el ``EmbeddingService`` real del Módulo C).

Cobertura:
- Alta end-to-end: una observación creada con fecha + formato y texto/clasif.
- Idempotencia (Requirement 1.1): subir el mismo archivo dos veces → una sola
  observación; una segunda educadora no reindexa ni re-almacena.
- Rechazo sin efectos secundarios (Requirement 1.3): sin ``id_nino`` o sin
  ``id_educadora`` no se almacena archivo ni se crea observación.
- Registro de ``fecha_observacion`` y ``formato_captura`` (Requirement 1.5).

Trazabilidad: Requirements 1.1, 1.3, 1.5.
"""

from __future__ import annotations

import io
from datetime import date
from typing import Any

import pytest

from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import Dominio, FormatoCaptura
from app.providers.classifier.base import Classifier
from app.providers.transcription.base import TranscriptionProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import (
    Base,
    Observacion as ObservacionORM,
    ObservacionManifestacion,
)
from app.repositories.storage.base import StorageRepo, StoredFile
from app.services.ingestion_service import (
    IngestionService,
    IngestionValidationError,
)


# ---------------------------------------------------------------------------
# Fakes locales de los puertos (sin tocar implementaciones hermanas)
# ---------------------------------------------------------------------------
class FakeStorage(StorageRepo):
    """Almacén en memoria: guarda los bytes y cuenta las operaciones ``put``."""

    def __init__(self) -> None:
        self.puestos: list[tuple[str, bytes]] = []

    def put(self, file: StoredFile) -> str:
        data = file.stream.read()
        ref = f"ref-{len(self.puestos)}-{file.filename}"
        self.puestos.append((ref, data))
        return ref

    def get_url(self, ref: str, expires_in: int = 300) -> str:
        return f"memory://{ref}"


class FakeTranscriber(TranscriptionProvider):
    """Transcriptor que devuelve un texto fijo y cuenta las invocaciones."""

    def __init__(self, texto: str = "texto transcrito") -> None:
        self._texto = texto
        self.llamadas: list[tuple[str, FormatoCaptura]] = []

    def transcribe(self, media_ref: str, formato: FormatoCaptura) -> str:
        self.llamadas.append((media_ref, formato))
        return self._texto


class FakeClassifier(Classifier):
    """Clasificador determinista que cuenta cuántas veces clasifica."""

    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def classify(self, texto: str) -> ClasificacionPropuesta:
        self.llamadas.append(texto)
        return ClasificacionPropuesta(
            nivel_estimado=4,
            dominios=[Dominio.socioemocional],
            manifestaciones=["MAN-001"],
            confianza=0.9,
            pendiente_clasificacion_manual=False,
        )


class FakeEmbeddingService:
    """Fake del puerto ``EmbeddingService`` (Protocol): registra indexaciones."""

    def __init__(self) -> None:
        self.indexados: list[tuple[str, str]] = []

    def index_observacion(self, id_observacion: str, texto: str) -> None:
        self.indexados.append((id_observacion, texto))


class FakeRelationalRepo(RelationalRepo):
    """Repo relacional en memoria: solo lo que la ingesta consume.

    Implementa los métodos abstractos del puerto; los no usados por la ingesta
    lanzan ``NotImplementedError`` para dejar explícito que no se ejercitan.
    """

    def __init__(self) -> None:
        self.observaciones: dict[str, ObservacionORM] = {}
        self.vinculos: list[ObservacionManifestacion] = []

    # --- CRUD genérico (lo que usa la ingesta) ----------------------------
    def add(self, entity: Base) -> Base:
        if isinstance(entity, ObservacionORM):
            self.observaciones[entity.id_observacion] = entity
        elif isinstance(entity, ObservacionManifestacion):
            self.vinculos.append(entity)
        else:  # pragma: no cover - no esperado en estos tests
            raise NotImplementedError(type(entity))
        return entity

    def add_all(self, entities: list[Base]) -> None:
        for entity in entities:
            self.add(entity)

    def get(self, model: type[Base], pk: Any) -> Base | None:
        if model is ObservacionORM:
            return self.observaciones.get(pk)
        raise NotImplementedError(model)  # pragma: no cover

    # --- Métodos no ejercitados por la ingesta ----------------------------
    def list(self, model: type[Base], **filters: Any) -> list[Base]:  # pragma: no cover
        raise NotImplementedError

    def delete(self, model: type[Base], pk: Any) -> bool:  # pragma: no cover
        raise NotImplementedError

    def count(self, model: type[Base], **filters: Any) -> int:  # pragma: no cover
        raise NotImplementedError

    def ninos_por_jardin(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def ninos_por_sala(self, id_jardin: str, sala_grupo: str):  # pragma: no cover
        raise NotImplementedError

    def observaciones_de_nino(self, id_nino: str):  # pragma: no cover
        raise NotImplementedError

    def manifestaciones_de_observacion(self, id_observacion: str):  # pragma: no cover
        raise NotImplementedError

    def bitacoras_de_nino(self, id_nino: str):  # pragma: no cover
        raise NotImplementedError

    def recomendaciones_de_nino(self, id_nino: str):  # pragma: no cover
        raise NotImplementedError

    def rubrica_vigente(self):  # pragma: no cover
        raise NotImplementedError

    def contar_ninos_por_sala(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def contar_decisiones(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    # --- Agregaciones periódicas (reporte de dirección, no ejercitadas) ---
    def conteos_nivel_por_sala(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles_por_sala(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles_por_dominio(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def contar_observaciones_periodo(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def contar_bitacoras_periodo(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def alertas_retroceso(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def alertas_inactividad(
        self, id_jardin, fecha_fin, dias: int = 14
    ):  # pragma: no cover
        raise NotImplementedError


def _file(contenido: bytes, nombre: str, tipo: str | None = None) -> StoredFile:
    return StoredFile(io.BytesIO(contenido), nombre, tipo)


def _service() -> tuple[
    IngestionService,
    FakeStorage,
    FakeTranscriber,
    FakeClassifier,
    FakeRelationalRepo,
    FakeEmbeddingService,
]:
    storage = FakeStorage()
    transcriber = FakeTranscriber()
    classifier = FakeClassifier()
    repo = FakeRelationalRepo()
    embeddings = FakeEmbeddingService()
    svc = IngestionService(storage, transcriber, classifier, repo, embeddings)
    return svc, storage, transcriber, classifier, repo, embeddings


# ---------------------------------------------------------------------------
# Alta end-to-end (flujo completo con fakes)
# ---------------------------------------------------------------------------
def test_ingesta_audio_crea_una_observacion_end_to_end() -> None:
    svc, storage, transcriber, classifier, repo, embeddings = _service()

    resultado = svc.ingest(
        id_nino="N-001",
        id_educadora="E-001",
        formato=FormatoCaptura.audio,
        archivo=_file(b"audio-bytes", "nota.mp3", "audio/mpeg"),
    )

    # Exactamente una observación creada, asociada al niño/a y la educadora.
    assert len(repo.observaciones) == 1
    assert resultado.duplicado is False
    assert resultado.id_nino == "N-001"
    assert resultado.id_educadora == "E-001"
    # Pasó por todo el flujo: storage → transcripción → clasificación → embed.
    assert len(storage.puestos) == 1
    assert len(transcriber.llamadas) == 1
    assert classifier.llamadas == ["texto transcrito"]
    assert embeddings.indexados == [(resultado.id_observacion, "texto transcrito")]
    # El vínculo de manifestación propuesta quedó persistido.
    assert [v.id_manifestacion for v in repo.vinculos] == ["MAN-001"]


def test_ingesta_texto_directo_no_transcribe_ni_almacena_archivo() -> None:
    svc, storage, transcriber, classifier, repo, _ = _service()

    resultado = svc.ingest(
        id_nino="N-002",
        id_educadora="E-001",
        formato=FormatoCaptura.texto,
        texto="  La niña comparte materiales con sus pares.  ",
    )

    assert len(repo.observaciones) == 1
    assert storage.puestos == []  # el texto directo no se almacena como medio
    assert transcriber.llamadas == []  # ni se transcribe (Requirement 2.5)
    assert resultado.texto == "La niña comparte materiales con sus pares."
    assert classifier.llamadas == [resultado.texto]


# ---------------------------------------------------------------------------
# Idempotencia (Requirement 1.1)
# ---------------------------------------------------------------------------
def test_mismo_archivo_dos_veces_no_crea_dos_observaciones() -> None:
    svc, storage, transcriber, classifier, repo, embeddings = _service()

    primera = svc.ingest(
        id_nino="N-001",
        id_educadora="E-001",
        formato=FormatoCaptura.foto,
        archivo=_file(b"foto-identica", "evidencia.jpg"),
    )
    segunda = svc.ingest(
        id_nino="N-001",
        id_educadora="E-001",
        formato=FormatoCaptura.foto,
        archivo=_file(b"foto-identica", "evidencia.jpg"),
    )

    # Una sola observación, y la segunda carga la reconoce como duplicada.
    assert len(repo.observaciones) == 1
    assert segunda.duplicado is True
    assert segunda.id_observacion == primera.id_observacion
    # No se repitieron los efectos secundarios de la ingesta.
    assert len(storage.puestos) == 1
    assert len(transcriber.llamadas) == 1
    assert len(classifier.llamadas) == 1
    assert len(embeddings.indexados) == 1


def test_texto_directo_identico_es_idempotente() -> None:
    svc, _, _, _, repo, _ = _service()
    for _ in range(2):
        svc.ingest(
            id_nino="N-010",
            id_educadora="E-002",
            formato=FormatoCaptura.texto,
            texto="mismo texto exacto",
        )
    assert len(repo.observaciones) == 1


def test_mismo_contenido_distinto_nino_son_observaciones_distintas() -> None:
    svc, _, _, _, repo, _ = _service()
    svc.ingest(
        id_nino="N-001",
        id_educadora="E-001",
        formato=FormatoCaptura.foto,
        archivo=_file(b"identico", "a.jpg"),
    )
    svc.ingest(
        id_nino="N-002",
        id_educadora="E-001",
        formato=FormatoCaptura.foto,
        archivo=_file(b"identico", "a.jpg"),
    )
    assert len(repo.observaciones) == 2


# ---------------------------------------------------------------------------
# Rechazo sin efectos secundarios (Requirement 1.3)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("id_nino", "id_educadora"),
    [(None, "E-001"), ("N-001", None), (None, None), ("", "E-001"), ("N-001", "")],
)
def test_rechaza_sin_nino_o_educadora_sin_efectos(
    id_nino: str | None, id_educadora: str | None
) -> None:
    svc, storage, transcriber, classifier, repo, embeddings = _service()

    with pytest.raises(IngestionValidationError):
        svc.ingest(
            id_nino=id_nino,
            id_educadora=id_educadora,
            formato=FormatoCaptura.audio,
            archivo=_file(b"audio", "nota.mp3"),
        )

    # Nada se almacenó ni se creó (Requirement 1.3).
    assert storage.puestos == []
    assert transcriber.llamadas == []
    assert classifier.llamadas == []
    assert repo.observaciones == {}
    assert embeddings.indexados == []


def test_error_de_validacion_lleva_mensaje_en_espanol() -> None:
    svc, *_ = _service()
    with pytest.raises(IngestionValidationError) as exc:
        svc.ingest(
            id_nino=None,
            id_educadora=None,
            formato=FormatoCaptura.texto,
            texto="hola",
        )
    assert "niño/a" in str(exc.value) and "educadora" in str(exc.value)


# ---------------------------------------------------------------------------
# Registro de fecha y formato (Requirement 1.5)
# ---------------------------------------------------------------------------
def test_registra_fecha_y_formato_captura() -> None:
    svc, _, _, _, repo, _ = _service()
    fecha = date(2026, 10, 13)

    resultado = svc.ingest(
        id_nino="N-003",
        id_educadora="E-001",
        formato=FormatoCaptura.video,
        archivo=_file(b"video-bytes", "clip.mp4", "video/mp4"),
        fecha_observacion=fecha,
    )

    obs = repo.observaciones[resultado.id_observacion]
    assert obs.fecha_observacion == fecha
    assert obs.formato_captura is FormatoCaptura.video
    assert resultado.fecha_observacion == fecha
    assert resultado.formato_captura is FormatoCaptura.video


def test_fecha_por_defecto_es_hoy() -> None:
    svc, _, _, _, repo, _ = _service()
    resultado = svc.ingest(
        id_nino="N-004",
        id_educadora="E-001",
        formato=FormatoCaptura.texto,
        texto="observación sin fecha explícita",
    )
    assert resultado.fecha_observacion == date.today()
