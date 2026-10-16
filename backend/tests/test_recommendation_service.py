"""Tests del ``RecommendationService`` (tarea 7.9 — Módulo F, Modelo 3).

Verifican la orquestación de la recomendación de nivel usando **solo fakes
locales** de los puertos (aislamiento del Módulo F, Requirement 13): no se
importan implementaciones concretas de módulos hermanos (ni el
``EmbeddingService`` real del Módulo C ni el ``VectorRepo`` real del Módulo B).
El único proveedor concreto reutilizado es ``MockLlmProvider``, que es la
implementación secundaria del propio puerto LLM y simula fallos de forma
determinista mediante el marcador ``__fail__``.

Cobertura:
- Abstención con <5 observaciones: no persiste y señala observaciones faltantes
  (Requirement 6.10).
- La decisión proviene de la rúbrica, no del LLM; el LLM solo argumenta
  (Requirements 6.2, 6.7).
- Resiliencia cuando el LLM falla: decisión conservada, argumento no disponible
  (Requirement 6.11).
- Resiliencia cuando el LLM excede el plazo máximo (Requirement 6.1/6.11).
- Registro de ``decision_educadora`` con uno de aceptó/rechazó/ajustó (6.9).
- Respuesta completa con tramo/núcleo/nivel/score/version_rubrica (6.5).
- Sugerencia proactiva al cruzar el umbral de avance (6.8).

Trazabilidad: Requirements 6.1, 6.2, 6.5, 6.7, 6.8, 6.9, 6.10, 6.11, 21.4.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

import pytest

from app.domain.models import DecisionNivel
from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider
from app.providers.llm.mock_llm import FAIL_MARKER, MockLlmProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import (
    Base,
    Nino as NinoORM,
    Observacion as ObservacionORM,
    Recomendacion as RecomendacionORM,
    RubricaVersion as RubricaVersionORM,
)
from app.repositories.vector.base import VectorRepo
from app.services.recommendation_service import (
    ARGUMENTO_NO_DISPONIBLE,
    MIN_OBSERVACIONES,
    RecommendationError,
    RecommendationService,
    RecommendationValidationError,
)
from app.domain.models import FormatoCaptura


# ---------------------------------------------------------------------------
# Rúbrica oficial mínima de prueba (3 tramos, 1 núcleo)
# ---------------------------------------------------------------------------
def _criterios() -> dict:
    """Rúbrica versionada de prueba: sala_cuna nivel 3 con 4 conductas."""
    return {
        "version": "test-v1",
        "tramos": {
            "sala_cuna": {
                "rango_etario_meses": [0, 24],
                "nucleos": {
                    "identidad_y_autonomia": {
                        "niveles": [
                            {
                                "n": 3,
                                "nombre": "Desarrollando",
                                "conductas_observables": [
                                    "camina sostenida sola distancias cortas",
                                    "explora objetos nuevos manipula curiosidad",
                                    "reconoce rutinas diarias cotidianas sala",
                                    "comparte juguetes pares cercanos interaccion",
                                ],
                            }
                        ]
                    }
                },
            },
        },
        "umbrales": {
            "cobertura_avanzar": 0.8,
            "nucleos_requeridos": ["identidad_y_autonomia"],
            "racha_retroceso": 3,
        },
    }


# ---------------------------------------------------------------------------
# Fakes locales de los puertos (sin tocar implementaciones hermanas)
# ---------------------------------------------------------------------------
class FakeVectorRepo(VectorRepo):
    """Repo vectorial en memoria: ``search`` devuelve lo configurado."""

    def __init__(self, resultados: list[dict[str, Any]] | None = None) -> None:
        self.resultados = resultados or []
        self.busquedas: list[tuple[list[float], dict[str, Any], int]] = []

    def index(self, doc: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    def search(
        self, query_embedding: list[float], filtros: dict[str, Any], k: int
    ) -> list[dict[str, Any]]:
        self.busquedas.append((query_embedding, filtros, k))
        return list(self.resultados)


class FakeEmbeddingPort:
    """Fake del puerto de embeddings: devuelve un vector determinista."""

    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.llamadas.append(text)
        return [float(len(text)), 1.0, 2.0]


class SlowLlm(LlmProvider):
    """LLM que duerme más que el plazo para ejercitar el timeout (6.11)."""

    def __init__(self, retraso: float) -> None:
        self._retraso = retraso

    def generate(self, prompt: str, context: str) -> str:
        time.sleep(self._retraso)
        return "argumento tardío que no debería llegar a tiempo"


class EchoLlm(LlmProvider):
    """LLM que devuelve un texto fijo e ignora la decisión (para 6.7)."""

    def __init__(self, texto: str = "AVANZAR siempre, da igual la rúbrica") -> None:
        self._texto = texto
        self.llamadas: list[tuple[str, str]] = []

    def generate(self, prompt: str, context: str) -> str:
        self.llamadas.append((prompt, context))
        return self._texto


class FakeRelationalRepo(RelationalRepo):
    """Repo relacional en memoria propio de estos tests.

    Implementa **todos** los métodos abstractos de ``RelationalRepo``. Los no
    ejercitados por la recomendación lanzan ``NotImplementedError`` para dejar
    explícito que no se usan (no se reutiliza el fake de la ingesta).
    """

    def __init__(
        self,
        *,
        ninos: dict[str, NinoORM] | None = None,
        observaciones: dict[str, list[ObservacionORM]] | None = None,
        rubrica: RubricaVersionORM | None = None,
    ) -> None:
        self.ninos = ninos or {}
        self._observaciones = observaciones or {}
        self.rubrica = rubrica
        self.recomendaciones: dict[str, RecomendacionORM] = {}

    # --- CRUD genérico (lo que usa la recomendación) ----------------------
    def add(self, entity: Base) -> Base:
        if isinstance(entity, RecomendacionORM):
            self.recomendaciones[entity.id_recomendacion] = entity
        else:  # pragma: no cover - no esperado en estos tests
            raise NotImplementedError(type(entity))
        return entity

    def get(self, model: type[Base], pk: Any) -> Base | None:
        if model is NinoORM:
            return self.ninos.get(pk)
        if model is RecomendacionORM:
            return self.recomendaciones.get(pk)
        raise NotImplementedError(model)  # pragma: no cover

    def observaciones_de_nino(self, id_nino: str) -> list[ObservacionORM]:
        return list(self._observaciones.get(id_nino, []))

    def recomendaciones_de_nino(self, id_nino: str) -> list[RecomendacionORM]:
        return [r for r in self.recomendaciones.values() if r.id_nino == id_nino]

    def rubrica_vigente(self) -> RubricaVersionORM | None:
        return self.rubrica

    # --- Métodos no ejercitados por la recomendación ----------------------
    def add_all(self, entities: list[Base]) -> None:  # pragma: no cover
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

    def manifestaciones_de_observacion(self, id_observacion: str):  # pragma: no cover
        raise NotImplementedError

    def bitacoras_de_nino(self, id_nino: str):  # pragma: no cover
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


# ---------------------------------------------------------------------------
# Builders de datos de prueba
# ---------------------------------------------------------------------------
def _nino(id_nino: str = "N-001") -> NinoORM:
    return NinoORM(
        id_nino=id_nino,
        id_jardin="J-001",
        fecha_nacimiento=date(2025, 10, 1),  # ~12 meses al 2026-10 → sala_cuna
        sexo_registrado="F",
        sala_grupo="sala-cuna-a",
        fecha_ingreso=date(2026, 1, 1),
    )


def _obs(id_obs: str, nota: str, nivel: int | None = None) -> ObservacionORM:
    return ObservacionORM(
        id_observacion=id_obs,
        id_nino="N-001",
        id_educadora="E-001",
        fecha_observacion=date(2026, 10, 1),
        formato_captura=FormatoCaptura.texto,
        nivel_estimado=nivel,
        nota_breve=nota,
    )


def _rubrica() -> RubricaVersionORM:
    return RubricaVersionORM(
        version_rubrica="test-v1",
        criterios=_criterios(),
        vigente_desde=date(2026, 1, 1),
        descripcion="rúbrica de prueba",
    )


def _observaciones_cobertura_total() -> list[ObservacionORM]:
    """Cinco observaciones que cubren las 4 conductas del nivel 3 (score 1.0)."""
    return [
        _obs("OBS-1", "camina sostenida sola distancias cortas en la sala"),
        _obs("OBS-2", "explora objetos nuevos manipula con curiosidad constante"),
        _obs("OBS-3", "reconoce rutinas diarias cotidianas de la sala jardin"),
        _obs("OBS-4", "comparte juguetes con pares cercanos en interaccion"),
        _obs("OBS-5", "camina sostenida sola distancias cortas nuevamente hoy"),
    ]


def _repo_con_cobertura(
    observaciones: list[ObservacionORM] | None = None,
) -> FakeRelationalRepo:
    obs = observaciones if observaciones is not None else _observaciones_cobertura_total()
    return FakeRelationalRepo(
        ninos={"N-001": _nino()},
        observaciones={"N-001": obs},
        rubrica=_rubrica(),
    )


def _service(
    repo: FakeRelationalRepo,
    llm: LlmProvider | None = None,
    *,
    timeout_segundos: float = 10.0,
    resultados_rag: list[dict[str, Any]] | None = None,
) -> RecommendationService:
    return RecommendationService(
        repo,
        FakeVectorRepo(resultados_rag),
        llm or MockLlmProvider(),
        FakeEmbeddingPort(),
        timeout_segundos=timeout_segundos,
    )


# ---------------------------------------------------------------------------
# Abstención por datos insuficientes (<5 observaciones) — Requirement 6.10
# ---------------------------------------------------------------------------
def test_abstencion_con_menos_de_cinco_observaciones_no_persiste() -> None:
    observaciones = [_obs(f"OBS-{i}", "nota cualquiera") for i in range(3)]
    repo = _repo_con_cobertura(observaciones)
    svc = _service(repo)

    resultado = svc.recomendar("N-001", "E-001", nivel_actual=3)

    assert resultado.datos_insuficientes is True
    assert resultado.persistida is False
    assert resultado.decision is None
    assert resultado.observaciones_registradas == 3
    # Faltan exactamente (5 - 3) = 2 observaciones.
    assert resultado.observaciones_faltantes == MIN_OBSERVACIONES - 3 == 2
    # No se persistió ninguna recomendación.
    assert repo.recomendaciones == {}


def test_abstencion_cero_observaciones_indica_faltan_cinco() -> None:
    repo = _repo_con_cobertura([])
    svc = _service(repo)
    resultado = svc.recomendar("N-001", "E-001", nivel_actual=3)
    assert resultado.datos_insuficientes is True
    assert resultado.observaciones_faltantes == MIN_OBSERVACIONES
    assert repo.recomendaciones == {}


# ---------------------------------------------------------------------------
# La decisión proviene de la rúbrica, no del LLM — Requirements 6.2, 6.7
# ---------------------------------------------------------------------------
def test_decision_proviene_de_la_rubrica_no_del_llm() -> None:
    # El LLM dice "AVANZAR" en su texto, pero las observaciones NO cubren el
    # umbral (solo 1 de 4 conductas) ⇒ la rúbrica decide MANTENER.
    observaciones = [
        _obs("OBS-1", "camina sostenida sola distancias cortas"),
        _obs("OBS-2", "nota sin relacion con conductas observables alguna"),
        _obs("OBS-3", "otra nota irrelevante para la cobertura del nivel"),
        _obs("OBS-4", "mas texto sin coincidencia de conductas observables"),
        _obs("OBS-5", "ultimo texto neutro sin señal de cobertura ninguna"),
    ]
    repo = _repo_con_cobertura(observaciones)
    svc = _service(repo, EchoLlm("AVANZAR AVANZAR AVANZAR"))

    resultado = svc.recomendar("N-001", "E-001", nivel_actual=3)

    assert resultado.decision is DecisionNivel.MANTENER
    assert resultado.score < 0.8
    # El argumento del LLM se adjunta pero NO altera la decisión determinista.
    assert resultado.argumento_disponible is True


def test_decision_avanzar_cuando_cobertura_total() -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo, EchoLlm("texto cualquiera"))

    resultado = svc.recomendar("N-001", "E-001", nivel_actual=3)

    assert resultado.decision is DecisionNivel.AVANZAR
    assert resultado.score == pytest.approx(1.0)
    assert resultado.persistida is True


def test_el_llm_solo_argumenta_y_no_recibe_poder_sobre_la_decision() -> None:
    repo = _repo_con_cobertura()
    echo = EchoLlm("RETROCEDER RETROCEDER")
    svc = _service(repo, echo)

    resultado = svc.recomendar("N-001", "E-001", nivel_actual=3)

    # El LLM fue invocado (argumenta) pero la decisión sigue siendo de la rúbrica.
    assert echo.llamadas, "el LLM debió invocarse para argumentar"
    assert resultado.decision is DecisionNivel.AVANZAR
    assert resultado.argumento_ia == "RETROCEDER RETROCEDER"


# ---------------------------------------------------------------------------
# Respuesta completa — Requirement 6.5
# ---------------------------------------------------------------------------
def test_respuesta_incluye_tramo_nucleo_nivel_score_version() -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo)

    r = svc.recomendar("N-001", "E-001", nivel_actual=3)

    assert r.tramo == "sala_cuna"
    assert r.nucleo == "identidad_y_autonomia"
    assert r.nivel_actual == 3
    assert 0.0 <= r.score <= 1.0
    assert r.version_rubrica == "test-v1"
    assert len(r.conductas_observables_cubiertas) == 4
    assert r.conductas_observables_pendientes == []
    # La evidencia cita observaciones por su identificador.
    assert all(e.startswith("OBS-") for e in r.evidencia)


def test_persiste_recomendacion_con_version_rubrica_y_conductas() -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo)

    r = svc.recomendar("N-001", "E-001", nivel_actual=3)

    assert r.id_recomendacion in repo.recomendaciones
    persistida = repo.recomendaciones[r.id_recomendacion]
    assert persistida.version_rubrica == "test-v1"
    assert persistida.decision is DecisionNivel.AVANZAR
    # Las columnas heredadas ``dominios_*`` guardan las conductas observables.
    assert persistida.dominios_cubiertos == r.conductas_observables_cubiertas
    assert persistida.dominios_pendientes == r.conductas_observables_pendientes
    assert persistida.decision_educadora is None  # aún no hay decisión humana


# ---------------------------------------------------------------------------
# Resiliencia del LLM — Requirement 6.11
# ---------------------------------------------------------------------------
class FailingLlm(LlmProvider):
    """LLM que siempre lanza ``LlmError`` (fallo del proveedor)."""

    def generate(self, prompt: str, context: str) -> str:
        raise LlmError("fallo simulado del proveedor")


def test_resiliencia_cuando_el_llm_falla_conserva_decision() -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo, FailingLlm())

    r = svc.recomendar("N-001", "E-001", nivel_actual=3)

    # La decisión determinista se conserva pese al fallo del LLM.
    assert r.decision is DecisionNivel.AVANZAR
    assert r.argumento_disponible is False
    assert r.argumento_ia == ARGUMENTO_NO_DISPONIBLE
    # Y la recomendación igualmente se persiste (no se descarta la decisión).
    assert r.persistida is True
    assert repo.recomendaciones[r.id_recomendacion].argumento_ia == ARGUMENTO_NO_DISPONIBLE


def test_resiliencia_cuando_el_llm_excede_el_plazo() -> None:
    repo = _repo_con_cobertura()
    # Plazo muy corto y un LLM lento ⇒ timeout.
    svc = _service(repo, SlowLlm(retraso=0.3), timeout_segundos=0.05)

    r = svc.recomendar("N-001", "E-001", nivel_actual=3)

    assert r.decision is DecisionNivel.AVANZAR
    assert r.argumento_disponible is False
    assert r.argumento_ia == ARGUMENTO_NO_DISPONIBLE
    assert r.persistida is True


# ---------------------------------------------------------------------------
# Registro de la decisión de la educadora — Requirement 6.9
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("entrada", "canonico"),
    [("aceptó", "aceptó"), ("rechazo", "rechazó"), ("Ajustó", "ajustó")],
)
def test_registrar_decision_educadora_persiste_valor_canonico(
    entrada: str, canonico: str
) -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo)
    r = svc.recomendar("N-001", "E-001", nivel_actual=3)

    actualizada = svc.registrar_decision_educadora(r.id_recomendacion, entrada)

    assert actualizada.decision_educadora == canonico
    assert repo.recomendaciones[r.id_recomendacion].decision_educadora == canonico


def test_registrar_decision_educadora_rechaza_valor_invalido() -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo)
    r = svc.recomendar("N-001", "E-001", nivel_actual=3)

    with pytest.raises(RecommendationValidationError):
        svc.registrar_decision_educadora(r.id_recomendacion, "tal vez")


def test_registrar_decision_educadora_recomendacion_inexistente() -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo)
    with pytest.raises(RecommendationError):
        svc.registrar_decision_educadora("no-existe", "aceptó")


# ---------------------------------------------------------------------------
# Sugerencia proactiva al cruzar el umbral — Requirement 6.8
# ---------------------------------------------------------------------------
def test_sugerir_avance_true_cuando_cruza_umbral() -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo)
    assert svc.sugerir_avance("N-001", nivel_actual=3) is True


def test_sugerir_avance_false_cuando_cobertura_parcial() -> None:
    observaciones = [
        _obs("OBS-1", "camina sostenida sola distancias cortas"),
        _obs("OBS-2", "nota irrelevante numero uno sin coincidencias"),
        _obs("OBS-3", "nota irrelevante numero dos sin coincidencias"),
        _obs("OBS-4", "nota irrelevante numero tres sin coincidencias"),
        _obs("OBS-5", "nota irrelevante numero cuatro sin coincidencias"),
    ]
    repo = _repo_con_cobertura(observaciones)
    svc = _service(repo)
    assert svc.sugerir_avance("N-001", nivel_actual=3) is False


def test_sugerir_avance_false_con_datos_insuficientes() -> None:
    repo = _repo_con_cobertura([_obs("OBS-1", "camina sostenida sola")])
    svc = _service(repo)
    assert svc.sugerir_avance("N-001", nivel_actual=3) is False


# ---------------------------------------------------------------------------
# Validación de entrada y precondiciones
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("id_nino", "id_educadora"),
    [(None, "E-001"), ("N-001", None), ("", "E-001"), ("N-001", "")],
)
def test_rechaza_sin_nino_o_educadora(id_nino, id_educadora) -> None:
    repo = _repo_con_cobertura()
    svc = _service(repo)
    with pytest.raises(RecommendationValidationError):
        svc.recomendar(id_nino, id_educadora, nivel_actual=3)
    assert repo.recomendaciones == {}


def test_error_si_nino_no_existe() -> None:
    repo = FakeRelationalRepo(ninos={}, observaciones={}, rubrica=_rubrica())
    svc = _service(repo)
    with pytest.raises(RecommendationError):
        svc.recomendar("N-999", "E-001", nivel_actual=3)


def test_error_si_no_hay_rubrica_vigente() -> None:
    repo = FakeRelationalRepo(
        ninos={"N-001": _nino()},
        observaciones={"N-001": _observaciones_cobertura_total()},
        rubrica=None,
    )
    svc = _service(repo)
    with pytest.raises(RecommendationError):
        svc.recomendar("N-001", "E-001", nivel_actual=3)


# ---------------------------------------------------------------------------
# Aislamiento: el fallo del RAG degrada sin romper la decisión
# ---------------------------------------------------------------------------
class BoomEmbeddings:
    """Puerto de embeddings que explota: el RAG debe degradar, no romper."""

    def embed(self, text: str) -> list[float]:
        raise RuntimeError("boom embeddings")


def test_rag_degrada_sin_romper_la_decision() -> None:
    repo = _repo_con_cobertura()
    svc = RecommendationService(
        repo, FakeVectorRepo(), MockLlmProvider(), BoomEmbeddings()
    )
    r = svc.recomendar("N-001", "E-001", nivel_actual=3)
    assert r.decision is DecisionNivel.AVANZAR
    assert r.persistida is True
