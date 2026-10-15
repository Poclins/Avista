"""Tests del seed del dataset E-1 (Requirement 10.2).

Verifican que el script de seed carga el dataset E-1 en la base relacional y
que los conteos de cada tabla coinciden con ``distribucion_y_validacion`` (la
fuente de verdad derivada del propio dataset), incluyendo:

- ``manifestaciones == 90`` (9 niveles × 5 dominios × 2),
- 18 manifestaciones por dominio y 10 por nivel,
- idempotencia: ejecutar el seed dos veces no altera los conteos.

Se usa una base SQLite en memoria para aislar cada test.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.domain.models import Dominio
from app.repositories.db import create_all, create_db_engine, create_session_factory
from app.repositories.relational.sqlalchemy_repo import SqlAlchemyRelationalRepo
from app.repositories.schema import (
    Base,
    Educadora,
    Jardin,
    Manifestacion,
    Nino,
    Observacion,
    ObservacionManifestacion,
    RubricaVersion,
    RutaNivel,
)
from app.repositories.seed.seed import (
    cargar_distribucion_y_validacion,
    seed,
)

# Mapea cada clave de conteo esperado a su modelo ORM.
MODELOS_POR_TABLA: dict[str, type[Base]] = {
    "jardines": Jardin,
    "educadoras": Educadora,
    "ninos": Nino,
    "ruta_niveles": RutaNivel,
    "manifestaciones": Manifestacion,
    "observaciones": Observacion,
    "observacion_manifestaciones": ObservacionManifestacion,
    "rubrica_versiones": RubricaVersion,
}


@pytest.fixture()
def session_factory():
    """Factoría de sesiones ligada a una base SQLite en memoria recién creada."""
    engine = create_db_engine("sqlite://")
    create_all(engine)
    return create_session_factory(engine)


@pytest.fixture()
def repo(session_factory):
    return SqlAlchemyRelationalRepo(session_factory)


@pytest.fixture()
def distribucion() -> dict:
    return cargar_distribucion_y_validacion()


def _contar(session_factory, model: type[Base]) -> int:
    with session_factory() as session:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_seed_devuelve_resumen_con_conteos_esperados(repo, distribucion) -> None:
    """El resumen devuelto por ``seed`` coincide con la distribución esperada."""
    resumen = seed(repo)
    assert resumen == distribucion["conteos"]


def test_conteos_de_cada_tabla_coinciden_con_distribucion(
    repo, session_factory, distribucion
) -> None:
    """Tras el seed, cada tabla tiene el número de filas esperado."""
    seed(repo)
    conteos = distribucion["conteos"]
    for tabla, model in MODELOS_POR_TABLA.items():
        assert _contar(session_factory, model) == conteos[tabla], tabla


def test_hay_exactamente_90_manifestaciones(repo, session_factory) -> None:
    """Requirement 10.2 / dataset E-1: 9 niveles × 5 dominios × 2 = 90."""
    seed(repo)
    assert _contar(session_factory, Manifestacion) == 90


def test_18_manifestaciones_por_dominio(repo, session_factory, distribucion) -> None:
    """Cada uno de los 5 dominios tiene 18 manifestaciones."""
    seed(repo)
    esperado = distribucion["manifestaciones_por_dominio"]
    with session_factory() as session:
        stmt = (
            select(Manifestacion.dominio, func.count())
            .group_by(Manifestacion.dominio)
        )
        reales = {
            (d.value if hasattr(d, "value") else str(d)): int(n)
            for d, n in session.execute(stmt).all()
        }
    assert reales == esperado
    assert set(reales) == {d.value for d in Dominio}
    assert all(v == 18 for v in reales.values())


def test_10_manifestaciones_por_nivel(repo, session_factory, distribucion) -> None:
    """Cada uno de los 9 niveles tiene 10 manifestaciones (5 dominios × 2)."""
    seed(repo)
    esperado = {int(k): v for k, v in distribucion["manifestaciones_por_nivel"].items()}
    with session_factory() as session:
        stmt = select(Manifestacion.nivel, func.count()).group_by(Manifestacion.nivel)
        reales = {int(nivel): int(n) for nivel, n in session.execute(stmt).all()}
    assert reales == esperado
    assert all(v == 10 for v in reales.values())


def test_seed_es_idempotente(repo, session_factory, distribucion) -> None:
    """Ejecutar el seed dos veces no duplica filas (merge por PK)."""
    seed(repo)
    primera = {
        tabla: _contar(session_factory, model)
        for tabla, model in MODELOS_POR_TABLA.items()
    }

    seed(repo)  # segunda ejecución
    segunda = {
        tabla: _contar(session_factory, model)
        for tabla, model in MODELOS_POR_TABLA.items()
    }

    assert primera == segunda
    assert segunda == distribucion["conteos"]


def test_integridad_referencial_de_las_observaciones(repo, session_factory) -> None:
    """Las FKs del dataset son consistentes (niños/educadoras/manifestaciones)."""
    seed(repo)
    with session_factory() as session:
        ninos = {n for (n,) in session.execute(select(Nino.id_nino)).all()}
        educadoras = {
            e for (e,) in session.execute(select(Educadora.id_educadora)).all()
        }
        manifestaciones = {
            m
            for (m,) in session.execute(
                select(Manifestacion.id_manifestacion)
            ).all()
        }

        for id_nino, id_edu in session.execute(
            select(Observacion.id_nino, Observacion.id_educadora)
        ).all():
            assert id_nino in ninos
            assert id_edu in educadoras

        for (id_manif,) in session.execute(
            select(ObservacionManifestacion.id_manifestacion)
        ).all():
            assert id_manif in manifestaciones
