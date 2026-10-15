"""Tests de edición y aprobación del ``BitacoraService`` (tarea 7.7 — Módulo F).

Verifican el ciclo de vida de la bitácora tras su generación (Requirements
5.7–5.9) usando **solo fakes locales** de los puertos (aislamiento del Módulo F,
Requirement 13): no se importan implementaciones concretas de módulos hermanos.

El fake relacional de este archivo implementa TODOS los métodos abstractos de
``RelationalRepo`` y, a diferencia del fake de generación (7.6), da lógica real a
``get`` y a ``add`` (fusión por clave primaria, como hace SQLAlchemy en
``session.merge``) para poder ejercitar la persistencia de la edición/estado.

Cobertura (criterios 5.7–5.9):
- 5.7 — Editar una bitácora en "borrador" persiste el nuevo texto.
- 5.8 — Aprobar una bitácora cambia su estado a "aprobada" y lo persiste;
  aprobar de nuevo es idempotente (no vuelve a "borrador").
- 5.9 — Editar una bitácora ya "aprobada" lanza el error de conflicto (→ 409) y
  no modifica el texto.
- Editar/aprobar una bitácora inexistente lanza el error 404.

Trazabilidad: Requirements 5.7, 5.8, 5.9.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.domain.models import EstadoBitacora
from app.providers.llm.mock_llm import MockLlmProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import Base, Bitacora as BitacoraORM
from app.repositories.vector.base import VectorRepo
from app.services.bitacora_service import (
    BitacoraConflictoError,
    BitacoraNoEncontradaError,
    BitacoraService,
)


# ---------------------------------------------------------------------------
# Fakes locales de los puertos (implementan TODOS los métodos abstractos)
# ---------------------------------------------------------------------------
class FakeRelationalRepo(RelationalRepo):
    """Repo relacional en memoria con ``get``/``add`` reales (fusión por PK).

    ``add`` imita a ``session.merge`` de SQLAlchemy: fusiona por clave primaria,
    de modo que persistir una bitácora ya existente actualiza su registro. Esto
    permite verificar que la edición y el cambio de estado quedan persistidos.
    El resto de métodos abstractos son stubs que lanzan ``NotImplementedError``
    porque la edición/aprobación no los ejercita (evita un fake incompleto).
    """

    def __init__(self) -> None:
        self.bitacoras: dict[str, BitacoraORM] = {}

    def set_bitacora(self, bitacora: BitacoraORM) -> None:
        self.bitacoras[bitacora.id_bitacora] = bitacora

    # --- CRUD usado por la edición/aprobación de bitácoras ----------------
    def add(self, entity: Base) -> Base:
        # Fusión por clave primaria (como session.merge): persiste el registro.
        if isinstance(entity, BitacoraORM):
            self.bitacoras[entity.id_bitacora] = entity
            return entity
        raise NotImplementedError(type(entity))  # pragma: no cover

    def get(self, model: type[Base], pk: Any) -> Base | None:
        if model is BitacoraORM:
            return self.bitacoras.get(pk)
        raise NotImplementedError(model)  # pragma: no cover

    # --- Métodos no ejercitados por la edición/aprobación -----------------
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
    """Índice vectorial mínimo (no se ejercita en edición/aprobación)."""

    def index(self, doc: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    def search(
        self, query_embedding: list[float], filtros: dict[str, Any], k: int
    ) -> list[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


class FakeEmbeddingProvider:
    """Fake del puerto ``EmbeddingPort`` (no se ejercita en edición/aprobación)."""

    def embed(self, text: str) -> list[float]:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helpers de construcción
# ---------------------------------------------------------------------------
def _bitacora(
    *,
    id_bitacora: str = "B-001",
    estado: EstadoBitacora = EstadoBitacora.borrador,
    texto: str = "Texto generado inicial.",
) -> BitacoraORM:
    return BitacoraORM(
        id_bitacora=id_bitacora,
        id_nino="N-001",
        id_educadora="E-001",
        periodo="2026-10-01/2026-10-14",
        texto_generado=texto,
        estado=estado,
        fecha=date(2026, 10, 14),
    )


def _service(
    bitacoras: list[BitacoraORM] | None = None,
) -> tuple[BitacoraService, FakeRelationalRepo]:
    repo = FakeRelationalRepo()
    for bit in bitacoras or []:
        repo.set_bitacora(bit)
    svc = BitacoraService(
        repo,
        FakeVectorRepo(),
        MockLlmProvider(),
        FakeEmbeddingProvider(),
    )
    return svc, repo


# ---------------------------------------------------------------------------
# 5.7 — Editar en "borrador" persiste el nuevo texto
# ---------------------------------------------------------------------------
def test_editar_en_borrador_persiste_el_texto() -> None:
    bit = _bitacora(texto="Texto original.")
    svc, repo = _service([bit])

    actualizada = svc.editar("B-001", "Texto corregido por la educadora.")

    # Se devuelve la bitácora con el texto nuevo y sigue en borrador.
    assert actualizada.texto_generado == "Texto corregido por la educadora."
    assert actualizada.estado is EstadoBitacora.borrador
    # El cambio quedó persistido en el repositorio (fusión por PK).
    assert (
        repo.bitacoras["B-001"].texto_generado
        == "Texto corregido por la educadora."
    )


# ---------------------------------------------------------------------------
# 5.8 — Aprobar cambia el estado a "aprobada" y lo persiste
# ---------------------------------------------------------------------------
def test_aprobar_cambia_estado_a_aprobada() -> None:
    bit = _bitacora(estado=EstadoBitacora.borrador)
    svc, repo = _service([bit])

    aprobada = svc.aprobar("B-001")

    assert aprobada.estado is EstadoBitacora.aprobada
    assert repo.bitacoras["B-001"].estado is EstadoBitacora.aprobada


def test_aprobar_es_idempotente_no_vuelve_a_borrador() -> None:
    # Una bitácora ya aprobada permanece aprobada al re-aprobar (5.8).
    bit = _bitacora(estado=EstadoBitacora.aprobada)
    svc, repo = _service([bit])

    aprobada = svc.aprobar("B-001")

    assert aprobada.estado is EstadoBitacora.aprobada
    assert repo.bitacoras["B-001"].estado is EstadoBitacora.aprobada


# ---------------------------------------------------------------------------
# 5.9 — Editar una aprobada lanza conflicto (409) y no cambia el texto
# ---------------------------------------------------------------------------
def test_editar_aprobada_lanza_conflicto_y_no_cambia_texto() -> None:
    bit = _bitacora(estado=EstadoBitacora.aprobada, texto="Texto aprobado.")
    svc, repo = _service([bit])

    with pytest.raises(BitacoraConflictoError) as exc:
        svc.editar("B-001", "Intento de edición no permitido.")

    assert "aprobada" in str(exc.value).lower()
    # El texto no se modificó (sigue siendo el aprobado).
    assert repo.bitacoras["B-001"].texto_generado == "Texto aprobado."
    assert repo.bitacoras["B-001"].estado is EstadoBitacora.aprobada


# ---------------------------------------------------------------------------
# 404 — Editar/aprobar una bitácora inexistente
# ---------------------------------------------------------------------------
def test_editar_inexistente_lanza_no_encontrada() -> None:
    svc, _ = _service([])
    with pytest.raises(BitacoraNoEncontradaError):
        svc.editar("B-404", "texto")


def test_aprobar_inexistente_lanza_no_encontrada() -> None:
    svc, _ = _service([])
    with pytest.raises(BitacoraNoEncontradaError):
        svc.aprobar("B-404")
