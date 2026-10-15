"""Tests del repositorio vectorial (Módulo C, tarea 4.2).

Cubren exhaustivamente la implementación en memoria (:class:`InMemoryVectorRepo`),
que es el camino verificable sin Postgres: indexar y luego buscar por
``id_observacion`` recupera exactamente un registro con los seis metadatos de
contrato (Requirement 4.3), el filtrado por metadatos acota el espacio de
búsqueda, y el orden por similitud coseno con tope ``k`` respeta el contrato de
la interfaz congelada (Requirement 4.7). También verifican la separación de
datos: solo ``id_nino`` seudónimo + texto/metadatos entran al índice
(Requirement 11.5).

Para la implementación pgvector (:class:`PgVectorRepo`) —que no puede correr
sobre SQLite— se verifica, con una conexión psycopg simulada, que el SQL use el
operador de distancia coseno ``<=>``, el UPSERT por ``id_observacion`` y los
filtros parametrizados, manteniendo el adaptador limpio y revisable.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.providers.errors import EmbeddingError
from app.repositories.vector import (
    InMemoryVectorRepo,
    PgVectorRepo,
    VectorRepo,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _doc(
    id_observacion: str,
    embedding: list[float],
    *,
    id_nino: str = "N-001",
    dominio: str = "cognitivo",
    nivel: int = 3,
    fecha: date | None = None,
    formato: str = "texto",
    texto: str = "El niño apiló cuatro bloques.",
) -> dict[str, Any]:
    """Documento-por-observación con los seis metadatos de contrato."""
    return {
        "id_observacion": id_observacion,
        "id_nino": id_nino,
        "dominio": dominio,
        "nivel": nivel,
        "fecha": fecha or date(2026, 10, 1),
        "formato": formato,
        "texto": texto,
        "embedding": embedding,
    }


# ===========================================================================
# InMemoryVectorRepo
# ===========================================================================
def test_memoria_es_vector_repo() -> None:
    """La implementación en memoria cumple la interfaz congelada del Módulo A."""
    assert isinstance(InMemoryVectorRepo(), VectorRepo)


def test_index_y_search_por_id_observacion_recupera_un_registro() -> None:
    """Requirement 4.3: buscar por ``id_observacion`` recupera exactamente uno."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-001", [1.0, 0.0, 0.0]))
    repo.index(_doc("O-002", [0.0, 1.0, 0.0], id_nino="N-002"))

    resultados = repo.search([1.0, 0.0, 0.0], {"id_observacion": "O-001"}, k=10)

    assert len(resultados) == 1
    recuperado = resultados[0]
    for metadato in ("id_observacion", "id_nino", "dominio", "nivel", "fecha", "formato"):
        assert metadato in recuperado
    assert recuperado["id_observacion"] == "O-001"


def test_search_devuelve_los_seis_metadatos_de_contrato() -> None:
    """Cada resultado transporta exactamente los seis metadatos de contrato."""
    repo = InMemoryVectorRepo()
    repo.index(
        _doc(
            "O-010",
            [1.0, 0.0],
            id_nino="N-010",
            dominio="socioemocional",
            nivel=5,
            fecha=date(2026, 9, 15),
            formato="audio",
        )
    )

    (doc,) = repo.search([1.0, 0.0], {"id_observacion": "O-010"}, k=1)

    assert doc["id_observacion"] == "O-010"
    assert doc["id_nino"] == "N-010"
    assert doc["dominio"] == "socioemocional"
    assert doc["nivel"] == 5
    assert doc["fecha"] == date(2026, 9, 15)
    assert doc["formato"] == "audio"


def test_reindexar_mismo_id_deja_un_unico_registro() -> None:
    """Indexar dos veces el mismo ``id_observacion`` reemplaza (sin duplicar)."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-001", [1.0, 0.0], nivel=2))
    repo.index(_doc("O-001", [1.0, 0.0], nivel=7))

    resultados = repo.search([1.0, 0.0], {"id_observacion": "O-001"}, k=10)

    assert len(resultados) == 1
    assert resultados[0]["nivel"] == 7


def test_filtrado_por_metadatos_acota_la_busqueda() -> None:
    """Los filtros de igualdad restringen el espacio de búsqueda."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-001", [1.0, 0.0], id_nino="N-001", dominio="cognitivo"))
    repo.index(_doc("O-002", [1.0, 0.0], id_nino="N-002", dominio="cognitivo"))
    repo.index(_doc("O-003", [1.0, 0.0], id_nino="N-001", dominio="motor_fino"))

    por_nino = repo.search([1.0, 0.0], {"id_nino": "N-001"}, k=10)
    assert {d["id_observacion"] for d in por_nino} == {"O-001", "O-003"}

    por_nino_y_dominio = repo.search(
        [1.0, 0.0], {"id_nino": "N-001", "dominio": "cognitivo"}, k=10
    )
    assert {d["id_observacion"] for d in por_nino_y_dominio} == {"O-001"}


def test_filtro_por_fecha_y_formato() -> None:
    """Se puede filtrar por ``fecha`` y por ``formato`` como metadatos."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-001", [1.0], fecha=date(2026, 1, 1), formato="texto"))
    repo.index(_doc("O-002", [1.0], fecha=date(2026, 2, 1), formato="foto"))

    por_fecha = repo.search([1.0], {"fecha": date(2026, 2, 1)}, k=10)
    assert [d["id_observacion"] for d in por_fecha] == ["O-002"]

    por_formato = repo.search([1.0], {"formato": "foto"}, k=10)
    assert [d["id_observacion"] for d in por_formato] == ["O-002"]


def test_orden_por_similitud_coseno_descendente() -> None:
    """Los resultados se ordenan por similitud coseno descendente."""
    repo = InMemoryVectorRepo()
    # Consulta alineada con [1, 0]. Coseno: O-align=1.0, O-45=~0.707, O-ortho=0.0.
    repo.index(_doc("O-align", [1.0, 0.0]))
    repo.index(_doc("O-45", [1.0, 1.0]))
    repo.index(_doc("O-ortho", [0.0, 1.0]))

    resultados = repo.search([1.0, 0.0], {}, k=10)

    assert [d["id_observacion"] for d in resultados] == ["O-align", "O-45", "O-ortho"]


def test_coseno_ignora_la_magnitud() -> None:
    """La similitud coseno depende de la dirección, no de la magnitud."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-escala", [10.0, 0.0]))  # misma dirección que la consulta
    repo.index(_doc("O-diag", [1.0, 1.0]))

    resultados = repo.search([1.0, 0.0], {}, k=10)
    assert resultados[0]["id_observacion"] == "O-escala"


def test_top_k_limita_el_numero_de_resultados() -> None:
    """``k`` limita cuántos vecinos se devuelven (los más similares)."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-align", [1.0, 0.0]))
    repo.index(_doc("O-45", [1.0, 1.0]))
    repo.index(_doc("O-ortho", [0.0, 1.0]))

    top2 = repo.search([1.0, 0.0], {}, k=2)
    assert [d["id_observacion"] for d in top2] == ["O-align", "O-45"]


def test_k_cero_o_negativo_devuelve_vacio() -> None:
    """Un ``k`` no positivo devuelve una lista vacía."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-001", [1.0, 0.0]))
    assert repo.search([1.0, 0.0], {}, k=0) == []
    assert repo.search([1.0, 0.0], {}, k=-1) == []


def test_search_sin_coincidencias_devuelve_vacio() -> None:
    """Un filtro sin coincidencias devuelve una lista vacía."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-001", [1.0, 0.0], id_nino="N-001"))
    assert repo.search([1.0, 0.0], {"id_nino": "N-999"}, k=10) == []


def test_index_falta_embedding_lanza_error() -> None:
    """Un documento sin ``embedding`` válido lanza ``EmbeddingError``."""
    repo = InMemoryVectorRepo()
    doc = _doc("O-001", [1.0])
    del doc["embedding"]
    with pytest.raises(EmbeddingError):
        repo.index(doc)


def test_index_falta_metadato_de_contrato_lanza_error() -> None:
    """Un documento sin uno de los seis metadatos lanza ``EmbeddingError``."""
    repo = InMemoryVectorRepo()
    doc = _doc("O-001", [1.0])
    del doc["dominio"]
    with pytest.raises(EmbeddingError):
        repo.index(doc)


def test_index_embedding_no_numerico_lanza_error() -> None:
    """Un ``embedding`` con valores no numéricos lanza ``EmbeddingError``."""
    repo = InMemoryVectorRepo()
    with pytest.raises(EmbeddingError):
        repo.index(_doc("O-001", ["a", "b"]))  # type: ignore[list-item]


def test_copia_defensiva_el_llamador_no_muta_el_indice() -> None:
    """Mutar el documento devuelto no altera el registro vigente del índice."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-001", [1.0, 0.0], nivel=3))

    (doc,) = repo.search([1.0, 0.0], {"id_observacion": "O-001"}, k=1)
    doc["nivel"] = 999

    (otra_vez,) = repo.search([1.0, 0.0], {"id_observacion": "O-001"}, k=1)
    assert otra_vez["nivel"] == 3


def test_privacidad_sin_nombre_ni_rut_en_el_indice() -> None:
    """Requirement 11.5: el índice solo guarda id_nino seudónimo + texto/metadatos."""
    repo = InMemoryVectorRepo()
    repo.index(_doc("O-001", [1.0, 0.0], id_nino="N-001"))

    (doc,) = repo.search([1.0, 0.0], {"id_observacion": "O-001"}, k=1)
    assert doc["id_nino"] == "N-001"
    assert "nombre" not in doc
    assert "rut" not in doc


# ===========================================================================
# PgVectorRepo — con conexión psycopg simulada (sin Postgres real)
# ===========================================================================
class _FakeCursor:
    """Cursor psycopg simulado que registra las ejecuciones."""

    def __init__(self, rows: list[tuple[Any, ...]] | None = None) -> None:
        self._rows = rows or []
        self.executed: list[tuple[str, Any]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


class _FakeConnection:
    """Conexión psycopg simulada, usable como context manager."""

    def __init__(self, rows: list[tuple[Any, ...]] | None = None) -> None:
        self.cursor_obj = _FakeCursor(rows)
        self.committed = False

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True


@pytest.fixture()
def _fake_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita depender del paquete pgvector real en estas pruebas de SQL.

    ``register_vector`` se vuelve un no-op y ``Vector`` una identidad, de modo
    que la lógica de SQL/parámetros se pueda verificar sin una conexión real.
    """
    import pgvector
    import pgvector.psycopg as pgpsy

    monkeypatch.setattr(pgpsy, "register_vector", lambda conn: None, raising=False)
    monkeypatch.setattr(pgvector, "Vector", lambda v: v, raising=False)


def test_pgvector_es_vector_repo() -> None:
    """La implementación pgvector cumple la interfaz congelada del Módulo A."""
    repo = PgVectorRepo(connection_factory=lambda: _FakeConnection(), dim=3)
    assert isinstance(repo, VectorRepo)


def test_pgvector_index_hace_upsert_por_id_observacion(_fake_pgvector: None) -> None:
    """``index`` emite un UPSERT (ON CONFLICT) sobre ``id_observacion``."""
    conn = _FakeConnection()
    repo = PgVectorRepo(connection_factory=lambda: conn, dim=3)

    repo.index(_doc("O-001", [1.0, 0.0, 0.0]))

    assert conn.committed is True
    sql, params = conn.cursor_obj.executed[-1]
    assert "INSERT INTO observacion_embeddings" in sql
    assert "ON CONFLICT (id_observacion) DO UPDATE" in sql
    # El primer parámetro es la PK; los seis metadatos de contrato viajan.
    assert params[0] == "O-001"
    assert params[1] == "N-001"


def test_pgvector_search_usa_distancia_coseno_y_limit(_fake_pgvector: None) -> None:
    """``search`` ordena por el operador coseno ``<=>`` con ``LIMIT k``."""
    rows = [("O-001", "N-001", "cognitivo", 3, date(2026, 10, 1), "texto", "txt", [1.0, 0.0, 0.0])]
    conn = _FakeConnection(rows)
    repo = PgVectorRepo(connection_factory=lambda: conn, dim=3)

    resultados = repo.search([1.0, 0.0, 0.0], {"id_nino": "N-001"}, k=5)

    sql, params = conn.cursor_obj.executed[-1]
    assert "<=>" in sql
    assert "ORDER BY embedding <=>" in sql
    assert "LIMIT %s" in sql
    assert "WHERE id_nino = %s" in sql
    # Último parámetro es k; penúltimo es el vector de consulta.
    assert params[-1] == 5
    assert resultados[0]["id_observacion"] == "O-001"
    assert resultados[0]["id_nino"] == "N-001"


def test_pgvector_search_k_no_positivo_no_consulta(_fake_pgvector: None) -> None:
    """Un ``k`` no positivo devuelve vacío sin tocar la base."""
    conn = _FakeConnection()
    repo = PgVectorRepo(connection_factory=lambda: conn, dim=3)
    assert repo.search([1.0, 0.0, 0.0], {}, k=0) == []
    assert conn.cursor_obj.executed == []


def test_pgvector_filtro_no_permitido_lanza_error(_fake_pgvector: None) -> None:
    """Filtrar por una columna fuera de la lista blanca lanza ``EmbeddingError``."""
    repo = PgVectorRepo(connection_factory=lambda: _FakeConnection(), dim=3)
    with pytest.raises(EmbeddingError):
        repo.search([1.0, 0.0, 0.0], {"columna_invalida": "x"}, k=5)


def test_pgvector_index_falta_metadato_lanza_error(_fake_pgvector: None) -> None:
    """Un documento sin un metadato de contrato lanza ``EmbeddingError``."""
    repo = PgVectorRepo(connection_factory=lambda: _FakeConnection(), dim=3)
    doc = _doc("O-001", [1.0, 0.0, 0.0])
    del doc["fecha"]
    with pytest.raises(EmbeddingError):
        repo.index(doc)


def test_pgvector_traduce_fallo_de_conexion_a_embedding_error(_fake_pgvector: None) -> None:
    """Un fallo de la conexión al indexar se traduce a ``EmbeddingError``."""

    def _boom() -> _FakeConnection:
        raise RuntimeError("Aurora no disponible")

    repo = PgVectorRepo(connection_factory=_boom, dim=3)
    with pytest.raises(EmbeddingError):
        repo.index(_doc("O-001", [1.0, 0.0, 0.0]))


def test_pgvector_dim_invalida() -> None:
    """Una dimensión no positiva se rechaza en construcción."""
    with pytest.raises(ValueError):
        PgVectorRepo(connection_factory=lambda: _FakeConnection(), dim=0)


# ===========================================================================
# Intercambiabilidad (LSP) — mismo contrato observable
# ===========================================================================
def test_ambas_implementaciones_son_vector_repo() -> None:
    """Memoria y pgvector exponen el mismo contrato ``VectorRepo``."""
    memoria = InMemoryVectorRepo()
    pg = PgVectorRepo(connection_factory=lambda: _FakeConnection(), dim=3)
    assert isinstance(memoria, VectorRepo)
    assert isinstance(pg, VectorRepo)
