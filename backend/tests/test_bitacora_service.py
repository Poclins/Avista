"""Tests del ``BitacoraService`` (tarea 7.6 — Módulo F, generación).

Verifican la generación de bitácoras (RAG + LLM) usando **solo fakes locales**
de los puertos (aislamiento del Módulo F, Requirement 13): no se importan
implementaciones concretas de módulos hermanos (ni el ``EmbeddingService`` real
del Módulo C, ni el vector/LLM reales). El ``MockLlmProvider`` ya existente se
usa como LLM, con su marcador ``__fail__`` para forzar un ``LlmError``.

Cobertura (criterios 5.1–5.6):
- Sin evidencia en el período ⇒ ``BitacoraSinEvidenciaError`` (→ HTTP 422) y no
  se persiste bitácora.
- El LLM falla ⇒ ``BitacoraLlmError`` (→ HTTP 503) y no se persiste bitácora.
- El LLM excede el plazo ⇒ ``BitacoraLlmError`` (→ HTTP 503) y no se persiste.
- Éxito ⇒ bitácora persistida en estado "borrador".
- Se recuperan hasta 20 observaciones similares vía ``VectorRepo``.
- El prompt/contexto exigen trazabilidad por identificador (Requirement 5.5).

Trazabilidad: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

import pytest

from app.domain.models import EstadoBitacora, FormatoCaptura
from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider
from app.providers.llm.mock_llm import FAIL_MARKER, MockLlmProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import (
    Base,
    Bitacora as BitacoraORM,
    Manifestacion as ManifestacionORM,
    Observacion as ObservacionORM,
    RubricaVersion as RubricaVersionORM,
)
from app.repositories.vector.base import VectorRepo
from app.services.bitacora_service import (
    MAX_SIMILARES,
    BitacoraLlmError,
    BitacoraService,
    BitacoraSinEvidenciaError,
)


# ---------------------------------------------------------------------------
# Fakes locales de los puertos (implementan TODOS los métodos abstractos)
# ---------------------------------------------------------------------------
class FakeRelationalRepo(RelationalRepo):
    """Repo relacional en memoria con todos los métodos abstractos del puerto.

    Solo los métodos que la generación de bitácoras consume tienen lógica real;
    el resto son stubs que lanzan ``NotImplementedError`` para dejar explícito
    que no se ejercitan (evita la deuda de un fake incompleto).
    """

    def __init__(self) -> None:
        self.observaciones: dict[str, ObservacionORM] = {}
        self.bitacoras: dict[str, BitacoraORM] = {}
        self.manifestaciones_por_obs: dict[str, list[ManifestacionORM]] = {}
        self.rubrica: RubricaVersionORM | None = None

    def set_observaciones(self, obs: list[ObservacionORM]) -> None:
        for o in obs:
            self.observaciones[o.id_observacion] = o

    # --- CRUD / consultas usadas por la generación de bitácoras -----------
    def add(self, entity: Base) -> Base:
        if isinstance(entity, BitacoraORM):
            self.bitacoras[entity.id_bitacora] = entity
        else:  # pragma: no cover - no esperado en estos tests
            raise NotImplementedError(type(entity))
        return entity

    def observaciones_de_nino(self, id_nino: str) -> list[ObservacionORM]:
        obs = [o for o in self.observaciones.values() if o.id_nino == id_nino]
        return sorted(obs, key=lambda o: o.fecha_observacion)

    def manifestaciones_de_observacion(
        self, id_observacion: str
    ) -> list[ManifestacionORM]:
        return list(self.manifestaciones_por_obs.get(id_observacion, []))

    def rubrica_vigente(self) -> RubricaVersionORM | None:
        return self.rubrica

    # --- Métodos no ejercitados por la generación de bitácoras ------------
    def add_all(self, entities: list[Base]) -> None:  # pragma: no cover
        raise NotImplementedError

    def get(self, model: type[Base], pk: Any) -> Base | None:  # pragma: no cover
        raise NotImplementedError

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

    def bitacoras_de_nino(self, id_nino: str):  # pragma: no cover
        raise NotImplementedError

    def recomendaciones_de_nino(self, id_nino: str):  # pragma: no cover
        raise NotImplementedError

    def contar_ninos_por_sala(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def contar_decisiones(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def conteos_nivel_por_sala(self, id_jardin, fecha_inicio, fecha_fin):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles_por_sala(self, id_jardin, fecha_inicio, fecha_fin):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles_por_dominio(self, id_jardin, fecha_inicio, fecha_fin):  # pragma: no cover
        raise NotImplementedError

    def contar_observaciones_periodo(self, id_jardin, fecha_inicio, fecha_fin):  # pragma: no cover
        raise NotImplementedError

    def contar_bitacoras_periodo(self, id_jardin, fecha_inicio, fecha_fin):  # pragma: no cover
        raise NotImplementedError

    def alertas_retroceso(self, id_jardin, fecha_inicio, fecha_fin):  # pragma: no cover
        raise NotImplementedError

    def alertas_inactividad(self, id_jardin, fecha_fin, dias=14):  # pragma: no cover
        raise NotImplementedError


class FakeVectorRepo(VectorRepo):
    """Índice vectorial en memoria: devuelve documentos preconfigurados.

    Registra las llamadas a ``search`` (embedding, filtros, k) para poder
    verificar que la generación pide hasta ``MAX_SIMILARES`` vecinos.
    """

    def __init__(self, resultados: list[dict[str, Any]] | None = None) -> None:
        self._resultados = resultados or []
        self.busquedas: list[tuple[list[float], dict[str, Any], int]] = []

    def index(self, doc: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    def search(
        self, query_embedding: list[float], filtros: dict[str, Any], k: int
    ) -> list[dict[str, Any]]:
        self.busquedas.append((query_embedding, filtros, k))
        return self._resultados[:k]


class FakeEmbeddingProvider:
    """Fake del puerto ``EmbeddingPort``: embedding determinista y trivial."""

    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.llamadas.append(text)
        return [float(len(text)), 1.0, 2.0]


class SlowLlmProvider(LlmProvider):
    """LLM que duerme más que el plazo, para probar el corte de 60 s (5.4)."""

    def __init__(self, retardo: float) -> None:
        self._retardo = retardo

    def generate(self, prompt: str, context: str) -> str:
        time.sleep(self._retardo)
        return "texto que nunca debería llegar a tiempo"


# ---------------------------------------------------------------------------
# Helpers de construcción
# ---------------------------------------------------------------------------
def _obs(
    id_observacion: str,
    *,
    id_nino: str = "N-001",
    fecha: date,
    nota: str = "La niña comparte materiales con sus pares.",
    nivel: int | None = 4,
) -> ObservacionORM:
    return ObservacionORM(
        id_observacion=id_observacion,
        id_nino=id_nino,
        id_educadora="E-001",
        fecha_observacion=fecha,
        formato_captura=FormatoCaptura.texto,
        nivel_estimado=nivel,
        nota_breve=nota,
    )


def _service(
    *,
    observaciones: list[ObservacionORM] | None = None,
    similares: list[dict[str, Any]] | None = None,
    llm: LlmProvider | None = None,
    plazo: float = 60.0,
    rubrica: RubricaVersionORM | None = None,
) -> tuple[BitacoraService, FakeRelationalRepo, FakeVectorRepo, FakeEmbeddingProvider]:
    repo = FakeRelationalRepo()
    if observaciones:
        repo.set_observaciones(observaciones)
    repo.rubrica = rubrica
    vector = FakeVectorRepo(similares)
    embeddings = FakeEmbeddingProvider()
    svc = BitacoraService(
        repo,
        vector,
        llm or MockLlmProvider(),
        embeddings,
        plazo_llm_segundos=plazo,
    )
    return svc, repo, vector, embeddings


# Período quincenal de referencia (ventana de 14 días).
INICIO = date(2026, 10, 1)
FIN = date(2026, 10, 14)


# ---------------------------------------------------------------------------
# 5.2 — Sin evidencia en el período ⇒ error 422, sin persistir
# ---------------------------------------------------------------------------
def test_sin_observaciones_en_periodo_lanza_sin_evidencia() -> None:
    # Observación fuera de la ventana → no cuenta como evidencia del período.
    fuera = _obs("O-fuera", fecha=date(2026, 9, 1))
    svc, repo, _, _ = _service(observaciones=[fuera])

    with pytest.raises(BitacoraSinEvidenciaError) as exc:
        svc.generar("N-001", "E-001", INICIO, FIN)

    assert "evidencia" in str(exc.value).lower()
    assert repo.bitacoras == {}  # no se persistió ninguna bitácora


def test_nino_sin_ninguna_observacion_lanza_sin_evidencia() -> None:
    svc, repo, _, _ = _service(observaciones=[])
    with pytest.raises(BitacoraSinEvidenciaError):
        svc.generar("N-999", "E-001", INICIO, FIN)
    assert repo.bitacoras == {}


# ---------------------------------------------------------------------------
# 5.3, 5.6 — Éxito ⇒ bitácora persistida en estado "borrador"
# ---------------------------------------------------------------------------
def test_generacion_exitosa_persiste_borrador() -> None:
    obs = [
        _obs("O-1", fecha=date(2026, 10, 3)),
        _obs("O-2", fecha=date(2026, 10, 10), nota="Resuelve un puzzle simple."),
    ]
    svc, repo, _, _ = _service(observaciones=obs)

    bitacora = svc.generar("N-001", "E-001", INICIO, FIN)

    # Persistida y en estado borrador (Requirement 5.6).
    assert len(repo.bitacoras) == 1
    assert bitacora.id_bitacora in repo.bitacoras
    assert bitacora.estado is EstadoBitacora.borrador
    assert bitacora.id_nino == "N-001"
    assert bitacora.id_educadora == "E-001"
    assert bitacora.periodo == "2026-10-01/2026-10-14"
    assert bitacora.texto_generado  # el LLM produjo texto


def test_solo_cuenta_observaciones_dentro_del_periodo() -> None:
    obs = [
        _obs("O-dentro", fecha=date(2026, 10, 5)),
        _obs("O-antes", fecha=date(2026, 9, 20)),
        _obs("O-despues", fecha=date(2026, 10, 20)),
    ]
    # LLM que captura el contexto para inspeccionar qué evidencia recibió.
    capturado: dict[str, str] = {}

    class CapturaLlm(LlmProvider):
        def generate(self, prompt: str, context: str) -> str:
            capturado["context"] = context
            capturado["prompt"] = prompt
            return "ok"

    svc, repo, _, _ = _service(observaciones=obs, llm=CapturaLlm())
    svc.generar("N-001", "E-001", INICIO, FIN)

    assert "O-dentro" in capturado["context"]
    assert "O-antes" not in capturado["context"]
    assert "O-despues" not in capturado["context"]


# ---------------------------------------------------------------------------
# 5.1 — Se recuperan hasta 20 observaciones similares vía VectorRepo
# ---------------------------------------------------------------------------
def test_recupera_hasta_veinte_similares_via_vector() -> None:
    obs = [_obs("O-1", fecha=date(2026, 10, 2))]
    # 25 documentos similares disponibles; el servicio pide k=20.
    similares = [
        {"id_observacion": f"S-{i}", "texto": f"evidencia similar {i}"}
        for i in range(25)
    ]
    svc, _, vector, embeddings = _service(observaciones=obs, similares=similares)

    svc.generar("N-001", "E-001", INICIO, FIN)

    # Se embebió la consulta y se buscó con k=20, filtrando por niño y ventana.
    assert embeddings.llamadas  # se formó una consulta semántica
    assert len(vector.busquedas) == 1
    _, filtros, k = vector.busquedas[0]
    assert k == MAX_SIMILARES == 20
    assert filtros["id_nino"] == "N-001"
    assert filtros["fecha_inicio"] == INICIO.isoformat()
    assert filtros["fecha_fin"] == FIN.isoformat()


def test_similares_duplicados_del_periodo_no_se_repiten() -> None:
    obs = [_obs("O-1", fecha=date(2026, 10, 2))]
    # El vector devuelve la misma observación del período + una nueva.
    similares = [
        {"id_observacion": "O-1", "texto": "duplicada del período"},
        {"id_observacion": "S-nueva", "texto": "evidencia nueva"},
    ]
    capturado: dict[str, str] = {}

    class CapturaLlm(LlmProvider):
        def generate(self, prompt: str, context: str) -> str:
            capturado["context"] = context
            return "ok"

    svc, _, _, _ = _service(
        observaciones=obs, similares=similares, llm=CapturaLlm()
    )
    svc.generar("N-001", "E-001", INICIO, FIN)

    # La sección RAG no vuelve a listar O-1 como evidencia similar.
    assert "evidencia nueva" in capturado["context"]
    assert "duplicada del período" not in capturado["context"]


# ---------------------------------------------------------------------------
# 5.5 — Trazabilidad: el prompt/contexto exigen citar por identificador
# ---------------------------------------------------------------------------
def test_contexto_y_prompt_exigen_trazabilidad_por_id() -> None:
    obs = [_obs("O-77", fecha=date(2026, 10, 4))]
    repo_man = ManifestacionORM(
        id_manifestacion="MAN-005",
        nivel=4,
        dominio="socioemocional",
        texto_observable="Comparte materiales.",
    )
    capturado: dict[str, str] = {}

    class CapturaLlm(LlmProvider):
        def generate(self, prompt: str, context: str) -> str:
            capturado["context"] = context
            capturado["prompt"] = prompt
            return "ok"

    svc, repo, _, _ = _service(observaciones=obs, llm=CapturaLlm())
    repo.manifestaciones_por_obs["O-77"] = [repo_man]

    svc.generar("N-001", "E-001", INICIO, FIN)

    # El prompt obliga a citar; el contexto expone los ids disponibles (5.5).
    assert "id_observacion" in capturado["prompt"]
    assert "cita" in capturado["prompt"].lower()
    assert "O-77" in capturado["context"]
    assert "MAN-005" in capturado["context"]


# ---------------------------------------------------------------------------
# 5.4 — El LLM falla ⇒ error 503, sin persistir bitácora
# ---------------------------------------------------------------------------
def test_llm_falla_lanza_error_503_y_no_persiste() -> None:
    # Nota con el marcador que fuerza LlmError en el MockLlmProvider.
    obs = [_obs("O-1", fecha=date(2026, 10, 2), nota=f"nota {FAIL_MARKER}")]
    svc, repo, _, _ = _service(observaciones=obs)

    with pytest.raises(BitacoraLlmError) as exc:
        svc.generar("N-001", "E-001", INICIO, FIN)

    assert "no pudo completarse" in str(exc.value).lower()
    assert repo.bitacoras == {}  # no se persistió bitácora en borrador


def test_llm_error_tipado_se_traduce_a_bitacora_llm_error() -> None:
    class SiempreFalla(LlmProvider):
        def generate(self, prompt: str, context: str) -> str:
            raise LlmError("fallo del proveedor")

    obs = [_obs("O-1", fecha=date(2026, 10, 2))]
    svc, repo, _, _ = _service(observaciones=obs, llm=SiempreFalla())

    with pytest.raises(BitacoraLlmError):
        svc.generar("N-001", "E-001", INICIO, FIN)
    assert repo.bitacoras == {}


# ---------------------------------------------------------------------------
# 5.4 — El LLM excede el plazo ⇒ error 503, sin persistir bitácora
# ---------------------------------------------------------------------------
def test_llm_excede_plazo_lanza_error_503_y_no_persiste() -> None:
    obs = [_obs("O-1", fecha=date(2026, 10, 2))]
    # Plazo muy corto (0.1 s) contra un LLM que tarda 2 s → corte verificable.
    svc, repo, _, _ = _service(
        observaciones=obs, llm=SlowLlmProvider(retardo=2.0), plazo=0.1
    )

    with pytest.raises(BitacoraLlmError) as exc:
        svc.generar("N-001", "E-001", INICIO, FIN)

    assert "tiempo máximo" in str(exc.value).lower()
    assert repo.bitacoras == {}


# ---------------------------------------------------------------------------
# Aislamiento: la rúbrica vigente entra al contexto cuando existe
# ---------------------------------------------------------------------------
def test_rubrica_vigente_se_incluye_en_contexto() -> None:
    obs = [_obs("O-1", fecha=date(2026, 10, 2))]
    rubrica = RubricaVersionORM(
        version_rubrica="v1",
        criterios={},
        vigente_desde=date(2026, 1, 1),
        descripcion="Rúbrica oficial Identidad y Autonomía.",
    )
    capturado: dict[str, str] = {}

    class CapturaLlm(LlmProvider):
        def generate(self, prompt: str, context: str) -> str:
            capturado["context"] = context
            return "ok"

    svc, _, _, _ = _service(observaciones=obs, llm=CapturaLlm(), rubrica=rubrica)
    svc.generar("N-001", "E-001", INICIO, FIN)

    assert "v1" in capturado["context"]
    assert "Identidad y Autonomía" in capturado["context"]
