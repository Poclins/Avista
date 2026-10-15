"""Tests unitarios del repositorio relacional (SQLite en memoria).

Validan el CRUD genérico, las consultas base de dominio y las agregaciones del
reporte de dirección sobre la implementación :class:`SqlAlchemyRelationalRepo`.
Trazabilidad: Requirement 4.4 (acceso vía interfaz, sin acoplamiento al SDK).
"""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.models import DecisionNivel, Dominio, EstadoBitacora, FormatoCaptura
from app.repositories.db import (
    create_all,
    create_db_engine,
    create_session_factory,
)
from app.repositories.relational import RelationalRepo, SqlAlchemyRelationalRepo
from app.repositories.schema import (
    Bitacora,
    Educadora,
    Jardin,
    Manifestacion,
    Nino,
    Observacion,
    ObservacionManifestacion,
    Recomendacion,
    RubricaVersion,
    RutaNivel,
)


@pytest.fixture()
def repo() -> SqlAlchemyRelationalRepo:
    """Repositorio sobre una base SQLite en memoria con el esquema creado."""
    engine = create_db_engine("sqlite:///:memory:")
    create_all(engine)
    factory = create_session_factory(engine)
    return SqlAlchemyRelationalRepo(factory)


def _seed_base(repo: SqlAlchemyRelationalRepo) -> None:
    """Siembra un jardín, una educadora y un niño/a mínimos."""
    repo.add(
        Jardin(
            id_jardin="J-001",
            nombre_fantasia="Los Girasoles",
            comuna="Maipú",
            region="RM",
            numero_salas=2,
            numero_educadoras=4,
        )
    )
    repo.add(
        Educadora(
            id_educadora="E-001",
            id_jardin="J-001",
            anios_experiencia=5,
        )
    )
    repo.add(
        Nino(
            id_nino="N-001",
            id_jardin="J-001",
            fecha_nacimiento=date(2021, 5, 10),
            sexo_registrado="F",
            sala_grupo="Sala Cuna",
            fecha_ingreso=date(2023, 3, 1),
        )
    )


# ---------------------------------------------------------------------------
# La implementación cumple la interfaz (DIP / Requirement 4.4)
# ---------------------------------------------------------------------------
def test_implementa_la_interfaz(repo: SqlAlchemyRelationalRepo) -> None:
    assert isinstance(repo, RelationalRepo)


# ---------------------------------------------------------------------------
# CRUD genérico
# ---------------------------------------------------------------------------
def test_add_y_get(repo: SqlAlchemyRelationalRepo) -> None:
    repo.add(
        Jardin(
            id_jardin="J-001",
            nombre_fantasia="Los Girasoles",
            comuna="Maipú",
            region="RM",
            numero_salas=2,
            numero_educadoras=4,
        )
    )
    recuperado = repo.get(Jardin, "J-001")
    assert recuperado is not None
    assert recuperado.nombre_fantasia == "Los Girasoles"


def test_get_inexistente_devuelve_none(repo: SqlAlchemyRelationalRepo) -> None:
    assert repo.get(Jardin, "NO-EXISTE") is None


def test_add_es_idempotente_por_pk(repo: SqlAlchemyRelationalRepo) -> None:
    """``add`` fusiona por PK: reinsertar actualiza en vez de duplicar."""
    _seed_base(repo)
    repo.add(
        Nino(
            id_nino="N-001",
            id_jardin="J-001",
            fecha_nacimiento=date(2021, 5, 10),
            sexo_registrado="M",  # cambia un campo
            sala_grupo="Sala Media",
            fecha_ingreso=date(2023, 3, 1),
        )
    )
    assert repo.count(Nino) == 1
    actualizado = repo.get(Nino, "N-001")
    assert actualizado is not None
    assert actualizado.sala_grupo == "Sala Media"


def test_add_all_y_count(repo: SqlAlchemyRelationalRepo) -> None:
    _seed_base(repo)
    repo.add_all(
        [
            Nino(
                id_nino="N-002",
                id_jardin="J-001",
                fecha_nacimiento=date(2021, 1, 1),
                sexo_registrado="M",
                sala_grupo="Sala Media",
                fecha_ingreso=date(2023, 3, 1),
            ),
            Nino(
                id_nino="N-003",
                id_jardin="J-001",
                fecha_nacimiento=date(2021, 2, 2),
                sexo_registrado="F",
                sala_grupo="Sala Media",
                fecha_ingreso=date(2023, 3, 1),
            ),
        ]
    )
    assert repo.count(Nino) == 3
    assert repo.count(Nino, sala_grupo="Sala Media") == 2


def test_list_con_filtros(repo: SqlAlchemyRelationalRepo) -> None:
    _seed_base(repo)
    ninos = repo.list(Nino, id_jardin="J-001")
    assert len(ninos) == 1
    assert ninos[0].id_nino == "N-001"
    assert repo.list(Nino, id_jardin="J-999") == []


def test_delete(repo: SqlAlchemyRelationalRepo) -> None:
    _seed_base(repo)
    assert repo.delete(Nino, "N-001") is True
    assert repo.get(Nino, "N-001") is None
    assert repo.delete(Nino, "N-001") is False


# ---------------------------------------------------------------------------
# Consultas base de dominio
# ---------------------------------------------------------------------------
def test_ninos_por_jardin_y_sala(repo: SqlAlchemyRelationalRepo) -> None:
    _seed_base(repo)
    repo.add(
        Nino(
            id_nino="N-002",
            id_jardin="J-001",
            fecha_nacimiento=date(2021, 1, 1),
            sexo_registrado="M",
            sala_grupo="Sala Media",
            fecha_ingreso=date(2023, 3, 1),
        )
    )
    assert len(repo.ninos_por_jardin("J-001")) == 2
    sala_cuna = repo.ninos_por_sala("J-001", "Sala Cuna")
    assert [n.id_nino for n in sala_cuna] == ["N-001"]


def test_observaciones_de_nino_ordenadas(repo: SqlAlchemyRelationalRepo) -> None:
    _seed_base(repo)
    repo.add(
        Observacion(
            id_observacion="O-002",
            id_nino="N-001",
            id_educadora="E-001",
            fecha_observacion=date(2024, 6, 10),
            formato_captura=FormatoCaptura.texto,
            nivel_estimado=4,
        )
    )
    repo.add(
        Observacion(
            id_observacion="O-001",
            id_nino="N-001",
            id_educadora="E-001",
            fecha_observacion=date(2024, 6, 1),
            formato_captura=FormatoCaptura.audio,
        )
    )
    obs = repo.observaciones_de_nino("N-001")
    assert [o.id_observacion for o in obs] == ["O-001", "O-002"]


def test_manifestaciones_de_observacion(repo: SqlAlchemyRelationalRepo) -> None:
    _seed_base(repo)
    repo.add(
        RutaNivel(
            nivel=2,
            nombre_nivel="Nivel 2",
            edad_min_meses=6,
            edad_max_meses=12,
            dominios=[Dominio.lenguaje_comunicacion.value],
        )
    )
    repo.add(
        Manifestacion(
            id_manifestacion="M-010",
            nivel=2,
            dominio=Dominio.lenguaje_comunicacion,
            texto_observable="Balbucea en respuesta a la voz.",
        )
    )
    repo.add(
        Observacion(
            id_observacion="O-001",
            id_nino="N-001",
            id_educadora="E-001",
            fecha_observacion=date(2024, 6, 1),
            formato_captura=FormatoCaptura.audio,
        )
    )
    repo.add(
        ObservacionManifestacion(
            id_observacion="O-001", id_manifestacion="M-010"
        )
    )
    manifs = repo.manifestaciones_de_observacion("O-001")
    assert [m.id_manifestacion for m in manifs] == ["M-010"]


def test_bitacoras_y_recomendaciones_de_nino(
    repo: SqlAlchemyRelationalRepo,
) -> None:
    _seed_base(repo)
    repo.add(
        Bitacora(
            id_bitacora="B-001",
            id_nino="N-001",
            id_educadora="E-001",
            periodo="2024-Q2-1",
            texto_generado="Resumen...",
            fecha=date(2024, 6, 15),
        )
    )
    bitacoras = repo.bitacoras_de_nino("N-001")
    assert len(bitacoras) == 1
    assert bitacoras[0].estado is EstadoBitacora.borrador

    repo.add(
        RubricaVersion(
            version_rubrica="v1",
            criterios={"n": 3},
            vigente_desde=date(2024, 1, 1),
        )
    )
    repo.add(
        Recomendacion(
            id_recomendacion="R-001",
            id_nino="N-001",
            id_educadora="E-001",
            decision=DecisionNivel.AVANZAR,
            score=0.82,
            dominios_cubiertos=[Dominio.cognitivo.value],
            dominios_pendientes=[],
            version_rubrica="v1",
            fecha=date(2024, 6, 20),
        )
    )
    recs = repo.recomendaciones_de_nino("N-001")
    assert len(recs) == 1
    assert recs[0].decision is DecisionNivel.AVANZAR


def test_rubrica_vigente_toma_la_mas_reciente(
    repo: SqlAlchemyRelationalRepo,
) -> None:
    assert repo.rubrica_vigente() is None
    repo.add(
        RubricaVersion(
            version_rubrica="v1",
            criterios={},
            vigente_desde=date(2024, 1, 1),
        )
    )
    repo.add(
        RubricaVersion(
            version_rubrica="v2",
            criterios={},
            vigente_desde=date(2024, 6, 1),
        )
    )
    vigente = repo.rubrica_vigente()
    assert vigente is not None
    assert vigente.version_rubrica == "v2"


# ---------------------------------------------------------------------------
# Agregaciones para el reporte de dirección (Modelo 4)
# ---------------------------------------------------------------------------
def test_contar_ninos_por_sala(repo: SqlAlchemyRelationalRepo) -> None:
    _seed_base(repo)
    repo.add_all(
        [
            Nino(
                id_nino="N-002",
                id_jardin="J-001",
                fecha_nacimiento=date(2021, 1, 1),
                sexo_registrado="M",
                sala_grupo="Sala Media",
                fecha_ingreso=date(2023, 3, 1),
            ),
            Nino(
                id_nino="N-003",
                id_jardin="J-001",
                fecha_nacimiento=date(2021, 2, 2),
                sexo_registrado="F",
                sala_grupo="Sala Media",
                fecha_ingreso=date(2023, 3, 1),
            ),
        ]
    )
    assert repo.contar_ninos_por_sala("J-001") == {
        "Sala Cuna": 1,
        "Sala Media": 2,
    }


def test_distribucion_niveles_ignora_no_clasificadas(
    repo: SqlAlchemyRelationalRepo,
) -> None:
    _seed_base(repo)
    repo.add_all(
        [
            Observacion(
                id_observacion="O-001",
                id_nino="N-001",
                id_educadora="E-001",
                fecha_observacion=date(2024, 6, 1),
                formato_captura=FormatoCaptura.texto,
                nivel_estimado=4,
            ),
            Observacion(
                id_observacion="O-002",
                id_nino="N-001",
                id_educadora="E-001",
                fecha_observacion=date(2024, 6, 2),
                formato_captura=FormatoCaptura.texto,
                nivel_estimado=4,
            ),
            Observacion(
                id_observacion="O-003",
                id_nino="N-001",
                id_educadora="E-001",
                fecha_observacion=date(2024, 6, 3),
                formato_captura=FormatoCaptura.texto,
                nivel_estimado=5,
            ),
            Observacion(
                id_observacion="O-004",
                id_nino="N-001",
                id_educadora="E-001",
                fecha_observacion=date(2024, 6, 4),
                formato_captura=FormatoCaptura.texto,
                nivel_estimado=None,  # sin clasificar → se omite
            ),
        ]
    )
    assert repo.distribucion_niveles("J-001") == {4: 2, 5: 1}


def test_contar_decisiones(repo: SqlAlchemyRelationalRepo) -> None:
    _seed_base(repo)
    repo.add(
        RubricaVersion(
            version_rubrica="v1",
            criterios={},
            vigente_desde=date(2024, 1, 1),
        )
    )
    repo.add_all(
        [
            Recomendacion(
                id_recomendacion="R-001",
                id_nino="N-001",
                id_educadora="E-001",
                decision=DecisionNivel.AVANZAR,
                score=0.9,
                dominios_cubiertos=[],
                dominios_pendientes=[],
                version_rubrica="v1",
                fecha=date(2024, 6, 1),
            ),
            Recomendacion(
                id_recomendacion="R-002",
                id_nino="N-001",
                id_educadora="E-001",
                decision=DecisionNivel.MANTENER,
                score=0.5,
                dominios_cubiertos=[],
                dominios_pendientes=[],
                version_rubrica="v1",
                fecha=date(2024, 6, 2),
            ),
            Recomendacion(
                id_recomendacion="R-003",
                id_nino="N-001",
                id_educadora="E-001",
                decision=DecisionNivel.AVANZAR,
                score=0.88,
                dominios_cubiertos=[],
                dominios_pendientes=[],
                version_rubrica="v1",
                fecha=date(2024, 6, 3),
            ),
        ]
    )
    assert repo.contar_decisiones("J-001") == {
        "AVANZAR": 2,
        "MANTENER": 1,
        "RETROCEDER": 0,
    }


def test_claves_foraneas_se_aplican_en_sqlite(
    repo: SqlAlchemyRelationalRepo,
) -> None:
    """La FK a jardines se aplica (PRAGMA foreign_keys=ON)."""
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        repo.add(
            Educadora(
                id_educadora="E-999",
                id_jardin="JARDIN-INEXISTENTE",
                anios_experiencia=1,
            )
        )
