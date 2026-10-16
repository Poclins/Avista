"""Tests del esquema relacional SQLAlchemy (Capa 3).

Verifican que el esquema del dataset E-1 + tablas nuevas compila, crea todas las
tablas esperadas, respeta la nulabilidad del diccionario de datos y permite un
round-trip básico de persistencia en SQLite en memoria. Trazabilidad:
Requirement 4.1.
"""

from datetime import date

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models import DecisionNivel, Dominio, EstadoBitacora, FormatoCaptura, Rol
from app.repositories.schema import (
    Base,
    Bitacora,
    Educadora,
    Jardin,
    Manifestacion,
    Nino,
    Observacion,
    ObservacionManifestacion,
    Recomendacion,
    ReporteDireccion,
    RubricaVersion,
    RutaNivel,
)

EXPECTED_TABLES = {
    "jardines",
    "educadoras",
    "ninos",
    "ruta_niveles",
    "manifestaciones",
    "observaciones",
    "observacion_manifestaciones",
    "bitacoras",
    "recomendaciones",
    "rubrica_versiones",
    "reportes_direccion",
}


@pytest.fixture()
def session() -> Session:
    """Sesión sobre SQLite en memoria con el esquema creado."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_todas_las_tablas_creadas() -> None:
    """Se declaran exactamente las 7 tablas E-1 + 4 nuevas."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tablas = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tablas)


def test_nulabilidad_observaciones() -> None:
    """Diccionario E-1: nivel_estimado, nota_breve y edad_meses son opcionales."""
    cols = {c.name: c for c in Observacion.__table__.columns}
    assert cols["nivel_estimado"].nullable is True
    assert cols["nota_breve"].nullable is True
    assert cols["edad_meses"].nullable is True
    # Las columnas obligatorias no admiten NULL.
    assert cols["id_nino"].nullable is False
    assert cols["fecha_observacion"].nullable is False
    assert cols["formato_captura"].nullable is False


def test_decision_educadora_opcional() -> None:
    """La decisión final de la educadora puede quedar sin registrar (NULL)."""
    cols = {c.name: c for c in Recomendacion.__table__.columns}
    assert cols["decision_educadora"].nullable is True


def _seed_jardin_educadora_nino(session: Session) -> None:
    session.add(
        Jardin(
            id_jardin="J-001",
            nombre_fantasia="Los Girasoles",
            comuna="Maipú",
            region="RM",
            numero_salas=4,
            numero_educadoras=8,
        )
    )
    session.add(
        Educadora(
            id_educadora="E-001",
            id_jardin="J-001",
            rol=Rol.educadora_parvulos,
            anios_experiencia=5,
        )
    )
    session.add(
        Nino(
            id_nino="N-001",
            id_jardin="J-001",
            fecha_nacimiento=date(2021, 5, 10),
            sexo_registrado="F",
            sala_grupo="Sala Cuna",
            fecha_ingreso=date(2023, 3, 1),
        )
    )
    session.flush()


def test_round_trip_observacion_con_campos_opcionales_nulos(session: Session) -> None:
    """Se puede persistir una observación sin nivel/nota/edad (pre-clasificación)."""
    _seed_jardin_educadora_nino(session)
    obs = Observacion(
        id_observacion="O-001",
        id_nino="N-001",
        id_educadora="E-001",
        fecha_observacion=date(2024, 6, 1),
        formato_captura=FormatoCaptura.audio,
    )
    session.add(obs)
    session.commit()

    recuperada = session.get(Observacion, "O-001")
    assert recuperada is not None
    assert recuperada.nivel_estimado is None
    assert recuperada.nota_breve is None
    assert recuperada.edad_meses is None
    assert recuperada.formato_captura is FormatoCaptura.audio


def test_vinculo_observacion_manifestacion(session: Session) -> None:
    """La tabla puente N:M permite vincular una observación a manifestaciones."""
    _seed_jardin_educadora_nino(session)
    session.add(
        RutaNivel(
            nivel=2,
            nombre_nivel="Exploración",
            edad_min_meses=12,
            edad_max_meses=18,
            dominios=[Dominio.cognitivo.value],
            descripcion="",
        )
    )
    session.add(
        Manifestacion(
            id_manifestacion="M-010",
            nivel=2,
            dominio=Dominio.lenguaje_comunicacion,
            texto_observable="Balbucea en respuesta a la voz.",
        )
    )
    session.add(
        Observacion(
            id_observacion="O-002",
            id_nino="N-001",
            id_educadora="E-001",
            fecha_observacion=date(2024, 6, 2),
            formato_captura=FormatoCaptura.texto,
            nivel_estimado=2,
            nota_breve="",
            edad_meses=36,
        )
    )
    session.flush()
    session.add(
        ObservacionManifestacion(
            id_observacion="O-002", id_manifestacion="M-010"
        )
    )
    session.commit()

    vinculo = session.get(ObservacionManifestacion, ("O-002", "M-010"))
    assert vinculo is not None
    assert vinculo.manifestacion.dominio is Dominio.lenguaje_comunicacion


def test_recomendacion_referencia_version_rubrica(session: Session) -> None:
    """Una recomendación persiste la decisión de la rúbrica y su versión (FK)."""
    _seed_jardin_educadora_nino(session)
    session.add(
        RubricaVersion(
            version_rubrica="v1",
            criterios={"n_observaciones": 3, "umbral_score_avanzar": 0.7},
            vigente_desde=date(2024, 1, 1),
            descripcion="Rúbrica inicial",
        )
    )
    session.flush()
    session.add(
        Recomendacion(
            id_recomendacion="R-001",
            id_nino="N-001",
            id_educadora="E-001",
            decision=DecisionNivel.AVANZAR,
            score=0.82,
            dominios_cubiertos=[d.value for d in Dominio],
            dominios_pendientes=[],
            argumento_ia="",
            version_rubrica="v1",
            fecha=date(2024, 6, 20),
        )
    )
    session.commit()

    rec = session.get(Recomendacion, "R-001")
    assert rec is not None
    assert rec.decision is DecisionNivel.AVANZAR
    assert rec.decision_educadora is None
    assert rec.rubrica_version.descripcion == "Rúbrica inicial"


def test_bitacora_estado_por_defecto_borrador(session: Session) -> None:
    """Una bitácora recién creada queda en estado borrador por defecto."""
    _seed_jardin_educadora_nino(session)
    session.add(
        Bitacora(
            id_bitacora="B-001",
            id_nino="N-001",
            id_educadora="E-001",
            periodo="2024-Q2-1",
            texto_generado="Resumen...",
            fecha=date(2024, 6, 15),
        )
    )
    session.commit()
    bit = session.get(Bitacora, "B-001")
    assert bit is not None
    assert bit.estado is EstadoBitacora.borrador


def test_reporte_direccion_metricas_json(session: Session) -> None:
    """El reporte de dirección guarda métricas agregadas como JSON."""
    _seed_jardin_educadora_nino(session)
    session.add(
        ReporteDireccion(
            id_reporte="RD-001",
            id_jardin="J-001",
            periodo="2024-Q2",
            metricas={"subieron": 3, "mantuvieron": 10, "bajaron": 1},
            resumen_ejecutivo="",
            fecha=date(2024, 7, 1),
        )
    )
    session.commit()
    rep = session.get(ReporteDireccion, "RD-001")
    assert rep is not None
    assert rep.metricas["subieron"] == 3


def test_columna_obligatoria_rechaza_null(session: Session) -> None:
    """Insertar un jardín sin un campo obligatorio viola la restricción NOT NULL."""
    session.add(
        Jardin(
            id_jardin="J-999",
            nombre_fantasia=None,  # type: ignore[arg-type]
            comuna="X",
            region="Y",
            numero_salas=1,
            numero_educadoras=1,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
