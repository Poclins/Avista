"""Tests del ``DirectorReportService`` (tarea 9.1 — Módulo G, Modelo 4).

Verifican la orquestación del reporte de dirección usando **solo fakes locales**
de los puertos (aislamiento, Requirement 13): no se importan implementaciones
concretas de módulos hermanos. El ``FakeRelationalRepo`` devuelve agregaciones
precalculadas (como lo haría ``RelationalRepo`` sobre SQL), de modo que estos
tests se centran en la lógica del servicio (validación de rango, KPI
determinista, resumen tolerante a fallos), no en el SQL (eso lo cubre
``test_relational_aggregations.py``).

Cobertura de criterios:
- **7.1/7.3** — el reporte reúne todas las métricas agregadas del repositorio.
- **7.2** — rango inválido (inicio > fin o fecha mal formada) → error en español
  sin tocar datos.
- **7.4** — KPI de tiempo ahorrado determinista a partir del volumen.
- **7.5** — resumen ejecutivo narrativo vía LLM a partir de las métricas.
- **7.6** — si el LLM falla/excede el plazo, el reporte conserva las métricas y
  marca el resumen como no disponible.
- **7.7** — jardín/sala sin datos ⇒ conteos en cero sin error.
- **7.8** — las cifras provienen del repositorio (SQL), no del LLM.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

import pytest

from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider
from app.providers.llm.mock_llm import FAIL_MARKER, MockLlmProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import Base, ReporteDireccion as ReporteDireccionORM
from app.services.director_report_service import (
    MINUTOS_AHORRADOS_POR_BITACORA,
    MINUTOS_AHORRADOS_POR_OBSERVACION,
    RESUMEN_NO_DISPONIBLE,
    DirectorReportService,
    ReporteRangoInvalidoError,
)

PERIODO_INICIO = date(2024, 6, 1)
PERIODO_FIN = date(2024, 6, 30)


# ---------------------------------------------------------------------------
# Fakes locales de los puertos
# ---------------------------------------------------------------------------
class FakeRelationalRepo(RelationalRepo):
    """Repo relacional en memoria que devuelve agregaciones precalculadas.

    Solo implementa las 7 consultas agregadas que consume el reporte más
    ``add`` (para la persistencia opcional). El resto lanza
    ``NotImplementedError`` para dejar explícito que el servicio no las usa.
    """

    def __init__(
        self,
        *,
        conteos: dict[str, dict[str, int]] | None = None,
        dist_sala: dict[str, dict[int, int]] | None = None,
        dist_dominio: dict[str, dict[int, int]] | None = None,
        observaciones: dict[str, Any] | None = None,
        bitacoras: dict[str, Any] | None = None,
        retroceso: list[str] | None = None,
        inactividad: list[str] | None = None,
    ) -> None:
        self._conteos = conteos if conteos is not None else {}
        self._dist_sala = dist_sala if dist_sala is not None else {}
        self._dist_dominio = dist_dominio if dist_dominio is not None else {}
        self._observaciones = (
            observaciones
            if observaciones is not None
            else {"total": 0, "por_educadora": {}}
        )
        self._bitacoras = (
            bitacoras if bitacoras is not None else {"total": 0, "por_educadora": {}}
        )
        self._retroceso = retroceso if retroceso is not None else []
        self._inactividad = inactividad if inactividad is not None else []
        self.persistidos: list[ReporteDireccionORM] = []
        self.llamadas: list[tuple[str, date, date]] = []

    # --- Persistencia opcional del reporte --------------------------------
    def add(self, entity: Base) -> Base:
        if isinstance(entity, ReporteDireccionORM):
            self.persistidos.append(entity)
            return entity
        raise NotImplementedError(type(entity))  # pragma: no cover

    # --- Agregaciones del reporte (las 7 consultas de 3.4) ----------------
    def conteos_nivel_por_sala(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[str, int]]:
        self.llamadas.append((id_jardin, fecha_inicio, fecha_fin))
        return self._conteos

    def distribucion_niveles_por_sala(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[int, int]]:
        return self._dist_sala

    def distribucion_niveles_por_dominio(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[int, int]]:
        return self._dist_dominio

    def contar_observaciones_periodo(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, Any]:
        return self._observaciones

    def contar_bitacoras_periodo(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, Any]:
        return self._bitacoras

    def alertas_retroceso(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> list[str]:
        return self._retroceso

    def alertas_inactividad(
        self, id_jardin: str, fecha_fin: date, dias: int = 14
    ) -> list[str]:
        return self._inactividad

    # --- Métodos no ejercitados por el reporte ----------------------------
    def add_all(self, entities: list[Base]) -> None:  # pragma: no cover
        raise NotImplementedError

    def get(self, model: type[Base], pk: Any) -> Base | None:  # pragma: no cover
        raise NotImplementedError

    def list(self, model: type[Base], **filters: Any):  # pragma: no cover
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


class SlowLlm(LlmProvider):
    """LLM que duerme más que el plazo para ejercitar el timeout (7.6)."""

    def __init__(self, retraso: float) -> None:
        self._retraso = retraso

    def generate(self, prompt: str, context: str) -> str:
        time.sleep(self._retraso)
        return "resumen tardío que no debería llegar a tiempo"


class EchoContextLlm(LlmProvider):
    """LLM que devuelve el contexto recibido, para inspeccionar qué se le pasó."""

    def __init__(self) -> None:
        self.llamadas: list[tuple[str, str]] = []

    def generate(self, prompt: str, context: str) -> str:
        self.llamadas.append((prompt, context))
        return f"RESUMEN basado en: {context}"


# ---------------------------------------------------------------------------
# Fixtures con un jardín "con datos"
# ---------------------------------------------------------------------------
def _repo_con_datos() -> FakeRelationalRepo:
    return FakeRelationalRepo(
        conteos={
            "Sala Cuna": {"subieron": 1, "mantuvieron": 1, "bajaron": 1},
            "Sala Media": {"subieron": 0, "mantuvieron": 1, "bajaron": 0},
        },
        dist_sala={"Sala Cuna": {3: 1, 4: 3}, "Sala Media": {7: 1}},
        dist_dominio={"cognitivo": {4: 2}, "socioemocional": {6: 1}},
        observaciones={"total": 8, "por_educadora": {"E-001": 6, "E-002": 2}},
        bitacoras={"total": 3, "por_educadora": {"E-001": 2, "E-002": 1}},
        retroceso=["N-002"],
        inactividad=["N-004", "N-005"],
    )


# ---------------------------------------------------------------------------
# El servicio depende solo de la interfaz (DIP / aislamiento)
# ---------------------------------------------------------------------------
def test_depende_solo_de_la_interfaz_relacional() -> None:
    repo = _repo_con_datos()
    assert isinstance(repo, RelationalRepo)
    service = DirectorReportService(repo, MockLlmProvider())
    resultado = service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)
    assert resultado.id_jardin == "J-001"


# ---------------------------------------------------------------------------
# 7.1 / 7.3 — el reporte reúne todas las métricas agregadas del repositorio
# ---------------------------------------------------------------------------
def test_reporte_incluye_todas_las_metricas() -> None:
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider())

    resultado = service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)
    m = resultado.metricas

    assert m["conteos_nivel_por_sala"]["Sala Cuna"] == {
        "subieron": 1,
        "mantuvieron": 1,
        "bajaron": 1,
    }
    assert m["distribucion_niveles_por_sala"]["Sala Media"] == {7: 1}
    assert m["distribucion_niveles_por_dominio"]["cognitivo"] == {4: 2}
    assert m["observaciones"] == {"total": 8, "por_educadora": {"E-001": 6, "E-002": 2}}
    assert m["bitacoras"] == {"total": 3, "por_educadora": {"E-001": 2, "E-002": 1}}
    assert m["alertas"] == {
        "retroceso": ["N-002"],
        "inactividad": ["N-004", "N-005"],
    }


def test_periodo_se_pasa_al_repositorio_con_ambos_extremos() -> None:
    """7.1: las agregaciones reciben el período solicitado (inclusive)."""
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider())
    service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)
    assert repo.llamadas[0] == ("J-001", PERIODO_INICIO, PERIODO_FIN)


# ---------------------------------------------------------------------------
# 7.2 — rango de fechas inválido
# ---------------------------------------------------------------------------
def test_rango_invertido_es_rechazado_sin_persistir() -> None:
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider())

    with pytest.raises(ReporteRangoInvalidoError) as exc:
        service.generar("J-001", PERIODO_FIN, PERIODO_INICIO)

    assert "rango de fechas es inválido" in str(exc.value).lower()
    # No se tocó el repositorio: ni agregaciones ni persistencia (7.2).
    assert repo.llamadas == []
    assert repo.persistidos == []


def test_fecha_mal_formada_es_rechazada() -> None:
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider())
    with pytest.raises(ReporteRangoInvalidoError):
        service.generar("J-001", "2024-06-01", PERIODO_FIN)  # type: ignore[arg-type]
    assert repo.llamadas == []


def test_rango_de_un_solo_dia_es_valido() -> None:
    """inicio == fin es un rango válido (ambos extremos inclusivos)."""
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider())
    resultado = service.generar("J-001", PERIODO_INICIO, PERIODO_INICIO)
    assert resultado.periodo == "2024-06-01/2024-06-01"


# ---------------------------------------------------------------------------
# 7.4 — KPI de tiempo ahorrado determinista
# ---------------------------------------------------------------------------
def test_kpi_tiempo_ahorrado_determinista() -> None:
    repo = _repo_con_datos()  # 8 observaciones, 3 bitácoras
    service = DirectorReportService(repo, MockLlmProvider())

    kpi = service.generar("J-001", PERIODO_INICIO, PERIODO_FIN).metricas[
        "kpi_tiempo_ahorrado"
    ]
    esperado_min = (
        8 * MINUTOS_AHORRADOS_POR_OBSERVACION + 3 * MINUTOS_AHORRADOS_POR_BITACORA
    )
    assert kpi["minutos_ahorrados"] == esperado_min
    assert kpi["observaciones"] == 8
    assert kpi["bitacoras"] == 3
    assert kpi["horas_ahorradas"] == round(esperado_min / 60.0, 2)


def test_kpi_es_reproducible() -> None:
    """El mismo volumen produce siempre el mismo KPI (determinismo, 7.4)."""
    service1 = DirectorReportService(_repo_con_datos(), MockLlmProvider())
    service2 = DirectorReportService(_repo_con_datos(), MockLlmProvider())
    k1 = service1.generar("J-001", PERIODO_INICIO, PERIODO_FIN).metricas[
        "kpi_tiempo_ahorrado"
    ]
    k2 = service2.generar("J-001", PERIODO_INICIO, PERIODO_FIN).metricas[
        "kpi_tiempo_ahorrado"
    ]
    assert k1 == k2


# ---------------------------------------------------------------------------
# 7.5 / 7.8 — resumen ejecutivo narrativo a partir SOLO de las métricas
# ---------------------------------------------------------------------------
def test_resumen_ejecutivo_disponible() -> None:
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider())
    resultado = service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)
    assert resultado.resumen_disponible is True
    assert resultado.resumen_ejecutivo
    assert resultado.resumen_ejecutivo != RESUMEN_NO_DISPONIBLE


def test_llm_recibe_las_metricas_agregadas_como_contexto() -> None:
    """7.8: el LLM solo narra; recibe las cifras ya calculadas en el contexto."""
    repo = _repo_con_datos()
    llm = EchoContextLlm()
    service = DirectorReportService(repo, llm)
    service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)

    assert len(llm.llamadas) == 1
    _, context = llm.llamadas[0]
    # Cifras provenientes del repositorio presentes en el contexto del LLM.
    assert "Sala Cuna" in context
    assert "N-002" in context  # alerta de retroceso
    assert "horas" in context.lower()  # KPI de tiempo


# ---------------------------------------------------------------------------
# 7.6 — resiliencia del resumen (el LLM falla o excede el plazo)
# ---------------------------------------------------------------------------
def test_llm_falla_entrega_reporte_con_metricas() -> None:
    """Si el LLM falla, el reporte conserva las métricas y marca el resumen."""

    class FailingLlm(LlmProvider):
        def generate(self, prompt: str, context: str) -> str:
            raise LlmError("fallo simulado del proveedor")

    repo = _repo_con_datos()
    service = DirectorReportService(repo, FailingLlm())
    resultado = service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)

    assert resultado.resumen_disponible is False
    assert resultado.resumen_ejecutivo == RESUMEN_NO_DISPONIBLE
    # Las métricas no se descartan (7.6).
    assert resultado.metricas["observaciones"]["total"] == 8
    assert resultado.metricas["kpi_tiempo_ahorrado"]["bitacoras"] == 3


def test_llm_excede_plazo_entrega_reporte_con_metricas() -> None:
    repo = _repo_con_datos()
    service = DirectorReportService(
        repo, SlowLlm(retraso=0.3), timeout_segundos=0.05
    )
    resultado = service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)
    assert resultado.resumen_disponible is False
    assert resultado.resumen_ejecutivo == RESUMEN_NO_DISPONIBLE
    assert resultado.metricas["observaciones"]["total"] == 8


def test_llm_vacio_marca_resumen_no_disponible() -> None:
    class EmptyLlm(LlmProvider):
        def generate(self, prompt: str, context: str) -> str:
            return "   "

    repo = _repo_con_datos()
    service = DirectorReportService(repo, EmptyLlm())
    resultado = service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)
    assert resultado.resumen_disponible is False


# ---------------------------------------------------------------------------
# 7.7 — jardín/sala sin datos ⇒ ceros, sin error
# ---------------------------------------------------------------------------
def test_jardin_sin_datos_genera_reporte_en_cero() -> None:
    repo = FakeRelationalRepo()  # todas las agregaciones vacías/cero
    service = DirectorReportService(repo, MockLlmProvider())

    resultado = service.generar("J-002", PERIODO_INICIO, PERIODO_FIN)

    m = resultado.metricas
    assert m["conteos_nivel_por_sala"] == {}
    assert m["distribucion_niveles_por_sala"] == {}
    assert m["observaciones"] == {"total": 0, "por_educadora": {}}
    assert m["bitacoras"] == {"total": 0, "por_educadora": {}}
    assert m["alertas"] == {"retroceso": [], "inactividad": []}
    assert m["kpi_tiempo_ahorrado"]["minutos_ahorrados"] == 0
    # Sin error, el reporte se genera igualmente (7.7).
    assert resultado.id_reporte


def test_sala_sin_movimiento_con_ceros() -> None:
    repo = FakeRelationalRepo(
        conteos={"Transición": {"subieron": 0, "mantuvieron": 0, "bajaron": 0}}
    )
    service = DirectorReportService(repo, MockLlmProvider())
    resultado = service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)
    assert resultado.metricas["conteos_nivel_por_sala"]["Transición"] == {
        "subieron": 0,
        "mantuvieron": 0,
        "bajaron": 0,
    }


# ---------------------------------------------------------------------------
# Persistencia opcional del reporte
# ---------------------------------------------------------------------------
def test_reporte_se_persiste_por_defecto() -> None:
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider())
    resultado = service.generar(
        "J-001", PERIODO_INICIO, PERIODO_FIN, fecha_reporte=date(2024, 7, 1)
    )
    assert len(repo.persistidos) == 1
    persistido = repo.persistidos[0]
    assert persistido.id_reporte == resultado.id_reporte
    assert persistido.id_jardin == "J-001"
    assert persistido.periodo == "2024-06-01/2024-06-30"
    assert persistido.fecha == date(2024, 7, 1)
    assert persistido.metricas == resultado.metricas


def test_persistir_desactivable() -> None:
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider(), persistir=False)
    service.generar("J-001", PERIODO_INICIO, PERIODO_FIN)
    assert repo.persistidos == []


def test_prompt_de_fallo_fuerza_resumen_no_disponible() -> None:
    """El marcador __fail__ del MockLlmProvider ejercita la rama de fallo."""
    repo = _repo_con_datos()
    service = DirectorReportService(repo, MockLlmProvider())
    # El id_jardin se interpola en el prompt; el marcador fuerza LlmError.
    resultado = service.generar(
        f"J-{FAIL_MARKER}", PERIODO_INICIO, PERIODO_FIN
    )
    assert resultado.resumen_disponible is False
