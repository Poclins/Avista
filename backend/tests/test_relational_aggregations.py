"""Tests de las consultas agregadas periódicas del reporte de dirección.

Verifican, en **aislamiento total** (solo ``RelationalRepo`` + su implementación
``SqlAlchemyRelationalRepo`` sobre SQLite en memoria, sin ningún otro módulo),
las agregaciones que el Módulo G consumirá vía interfaz (tarea 3.4):

- ``conteos_nivel_por_sala``            → Requirement 7.1
- ``distribucion_niveles_por_sala``     → Requirement 7.3
- ``distribucion_niveles_por_dominio``  → Requirement 7.3
- ``contar_observaciones_periodo``      → Requirement 7.3
- ``contar_bitacoras_periodo``          → Requirement 7.3
- ``alertas_retroceso``                 → Requirement 7.3
- ``alertas_inactividad`` (14 días)     → Requirement 7.3

Cada agregación se contrasta contra una **fixture sembrada con valores
conocidos** cuyos resultados esperados se calculan a mano en el propio test.
El dataset está diseñado para cubrir los casos de borde relevantes:

- Niños/as que suben, mantienen y bajan dentro del período.
- Una sala sin movimiento (debe aparecer con ceros, Requirement 7.7).
- Observaciones fuera del período (deben excluirse de todas las métricas).
- Observaciones sin ``nivel_estimado`` (se omiten de distribuciones/conteos de
  nivel pero cuentan para el total de observaciones).
- Niños/as con y sin actividad en la ventana de inactividad de 14 días.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.models import Dominio, FormatoCaptura
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
    RutaNivel,
)

# Período de referencia usado por todos los tests (ambos extremos inclusivos).
PERIODO_INICIO = date(2024, 6, 1)
PERIODO_FIN = date(2024, 6, 30)


@pytest.fixture()
def repo() -> SqlAlchemyRelationalRepo:
    """Repositorio sobre una base SQLite en memoria con el esquema creado."""
    engine = create_db_engine("sqlite://")
    create_all(engine)
    factory = create_session_factory(engine)
    return SqlAlchemyRelationalRepo(factory)


def _obs(
    id_obs: str,
    id_nino: str,
    fecha: date,
    nivel: int | None,
    *,
    id_educadora: str = "E-001",
    formato: FormatoCaptura = FormatoCaptura.texto,
) -> Observacion:
    return Observacion(
        id_observacion=id_obs,
        id_nino=id_nino,
        id_educadora=id_educadora,
        fecha_observacion=fecha,
        formato_captura=formato,
        nivel_estimado=nivel,
    )


@pytest.fixture()
def seeded(repo: SqlAlchemyRelationalRepo) -> SqlAlchemyRelationalRepo:
    """Siembra un jardín con 2 salas, 2 educadoras, 5 niños/as y evidencia.

    Diseño de la fixture (todo dentro del jardín ``J-001``):

    Sala Cuna
      - N-001: 4 (01-jun) → 6 (20-jun)   ⇒ SUBE
      - N-002: 5 (02-jun) → 3 (18-jun)   ⇒ BAJA   (y dispara alerta de retroceso)
      - N-003: 4 (05-jun) → 4 (25-jun)   ⇒ MANTIENE

    Sala Media
      - N-004: 7 (10-jun) solo una obs    ⇒ MANTIENE (inicio == cierre)
      - N-005: sin observaciones con nivel en el período
               (tiene una obs sin nivel el 03-jun y una con nivel FUERA del
                período el 10-may) ⇒ se omite de conteos de nivel por sala.

    Observaciones fuera del período (deben excluirse de todo):
      - N-001 el 10-may con nivel 9 (previo al período).

    Inactividad (ventana de 14 días previos a 30-jun → (16-jun, 30-jun]):
      - Activos en la ventana: N-001 (20-jun), N-002 (18-jun), N-003 (25-jun).
      - Inactivos: N-004 (última obs 10-jun) y N-005 (03-jun) ⇒ alerta.
    """
    repo.add(
        Jardin(
            id_jardin="J-001",
            nombre_fantasia="Los Girasoles",
            comuna="Maipú",
            region="RM",
            numero_salas=2,
            numero_educadoras=2,
        )
    )
    repo.add_all(
        [
            Educadora(id_educadora="E-001", id_jardin="J-001", anios_experiencia=5),
            Educadora(id_educadora="E-002", id_jardin="J-001", anios_experiencia=3),
        ]
    )
    repo.add_all(
        [
            Nino(
                id_nino="N-001",
                id_jardin="J-001",
                fecha_nacimiento=date(2021, 5, 10),
                sexo_registrado="F",
                sala_grupo="Sala Cuna",
                fecha_ingreso=date(2023, 3, 1),
            ),
            Nino(
                id_nino="N-002",
                id_jardin="J-001",
                fecha_nacimiento=date(2021, 1, 1),
                sexo_registrado="M",
                sala_grupo="Sala Cuna",
                fecha_ingreso=date(2023, 3, 1),
            ),
            Nino(
                id_nino="N-003",
                id_jardin="J-001",
                fecha_nacimiento=date(2021, 2, 2),
                sexo_registrado="F",
                sala_grupo="Sala Cuna",
                fecha_ingreso=date(2023, 3, 1),
            ),
            Nino(
                id_nino="N-004",
                id_jardin="J-001",
                fecha_nacimiento=date(2020, 1, 1),
                sexo_registrado="M",
                sala_grupo="Sala Media",
                fecha_ingreso=date(2023, 3, 1),
            ),
            Nino(
                id_nino="N-005",
                id_jardin="J-001",
                fecha_nacimiento=date(2020, 2, 2),
                sexo_registrado="F",
                sala_grupo="Sala Media",
                fecha_ingreso=date(2023, 3, 1),
            ),
        ]
    )

    # Ruta/manifestaciones mínimas para derivar dominio por observación.
    repo.add_all(
        [
            RutaNivel(
                nivel=4,
                nombre_nivel="Nivel 4",
                edad_min_meses=24,
                edad_max_meses=36,
                dominios=[Dominio.cognitivo.value],
            ),
            RutaNivel(
                nivel=6,
                nombre_nivel="Nivel 6",
                edad_min_meses=36,
                edad_max_meses=48,
                dominios=[Dominio.socioemocional.value],
            ),
        ]
    )
    repo.add_all(
        [
            Manifestacion(
                id_manifestacion="M-COG",
                nivel=4,
                dominio=Dominio.cognitivo,
                texto_observable="Resuelve un encaje simple.",
            ),
            Manifestacion(
                id_manifestacion="M-SOC",
                nivel=6,
                dominio=Dominio.socioemocional,
                texto_observable="Comparte un juguete espontáneamente.",
            ),
        ]
    )

    # Observaciones (ver docstring para el diseño de los casos).
    repo.add_all(
        [
            # N-001: sube 4 → 6 (más una previa fuera del período).
            _obs("O-PRE", "N-001", date(2024, 5, 10), 9),  # fuera del período
            _obs("O-001", "N-001", PERIODO_INICIO, 4),
            _obs("O-002", "N-001", date(2024, 6, 20), 6),
            # N-002: baja 5 → 3 (retroceso).
            _obs("O-003", "N-002", date(2024, 6, 2), 5),
            _obs("O-004", "N-002", date(2024, 6, 18), 3),
            # N-003: mantiene 4 → 4.
            _obs("O-005", "N-003", date(2024, 6, 5), 4),
            _obs("O-006", "N-003", date(2024, 6, 25), 4),
            # N-004: una sola obs con nivel (mantiene), educadora E-002.
            _obs("O-007", "N-004", date(2024, 6, 10), 7, id_educadora="E-002"),
            # N-005: una obs sin nivel dentro del período + una con nivel fuera.
            _obs("O-008", "N-005", date(2024, 6, 3), None, id_educadora="E-002"),
            _obs("O-009", "N-005", date(2024, 5, 10), 2, id_educadora="E-002"),
        ]
    )

    # Vínculos observación↔manifestación para derivar el dominio.
    # Dominio cognitivo: O-001 (nivel 4) y O-005 (nivel 4).
    # Dominio socioemocional: O-002 (nivel 6).
    repo.add_all(
        [
            ObservacionManifestacion(id_observacion="O-001", id_manifestacion="M-COG"),
            ObservacionManifestacion(id_observacion="O-005", id_manifestacion="M-COG"),
            ObservacionManifestacion(id_observacion="O-002", id_manifestacion="M-SOC"),
        ]
    )

    # Bitácoras: 2 de E-001 y 1 de E-002 dentro del período; 1 fuera (excluir).
    repo.add_all(
        [
            Bitacora(
                id_bitacora="B-001",
                id_nino="N-001",
                id_educadora="E-001",
                periodo="2024-06-Q1",
                texto_generado="...",
                fecha=date(2024, 6, 15),
            ),
            Bitacora(
                id_bitacora="B-002",
                id_nino="N-002",
                id_educadora="E-001",
                periodo="2024-06-Q2",
                texto_generado="...",
                fecha=date(2024, 6, 28),
            ),
            Bitacora(
                id_bitacora="B-003",
                id_nino="N-004",
                id_educadora="E-002",
                periodo="2024-06-Q1",
                texto_generado="...",
                fecha=date(2024, 6, 12),
            ),
            Bitacora(
                id_bitacora="B-004",
                id_nino="N-001",
                id_educadora="E-001",
                periodo="2024-05",
                texto_generado="...",
                fecha=date(2024, 5, 30),  # fuera del período → se excluye
            ),
        ]
    )
    return repo


# ---------------------------------------------------------------------------
# La implementación concreta cumple la interfaz (DIP / aislamiento)
# ---------------------------------------------------------------------------
def test_usa_solo_la_interfaz_relacional(seeded: SqlAlchemyRelationalRepo) -> None:
    """El sujeto bajo prueba es la implementación del puerto, sin otros módulos."""
    assert isinstance(seeded, RelationalRepo)


# ---------------------------------------------------------------------------
# 7.1 — Conteo subieron/mantuvieron/bajaron por sala
# ---------------------------------------------------------------------------
def test_conteos_nivel_por_sala(seeded: SqlAlchemyRelationalRepo) -> None:
    resultado = seeded.conteos_nivel_por_sala(
        "J-001", PERIODO_INICIO, PERIODO_FIN
    )
    assert resultado == {
        "Sala Cuna": {"subieron": 1, "mantuvieron": 1, "bajaron": 1},
        "Sala Media": {"subieron": 0, "mantuvieron": 1, "bajaron": 0},
    }


def test_conteos_nivel_cada_nino_en_una_sola_categoria(
    seeded: SqlAlchemyRelationalRepo,
) -> None:
    """Requirement 7.1: cada niño/a cuenta en exactamente una categoría.

    4 niños/as tienen observaciones con nivel dentro del período
    (N-001..N-004); N-005 no (su única obs del período no tiene nivel), así que
    se omite. La suma total de las tres categorías debe ser 4.
    """
    resultado = seeded.conteos_nivel_por_sala(
        "J-001", PERIODO_INICIO, PERIODO_FIN
    )
    total = sum(
        categoria
        for sala in resultado.values()
        for categoria in sala.values()
    )
    assert total == 4


def test_conteos_nivel_lista_salas_sin_movimiento(
    seeded: SqlAlchemyRelationalRepo,
) -> None:
    """Requirement 7.7: una sala sin movimiento aparece con ceros."""
    # Añadimos una tercera sala sin ninguna observación en el período.
    seeded.add(
        Nino(
            id_nino="N-006",
            id_jardin="J-001",
            fecha_nacimiento=date(2019, 1, 1),
            sexo_registrado="M",
            sala_grupo="Transición",
            fecha_ingreso=date(2023, 3, 1),
        )
    )
    resultado = seeded.conteos_nivel_por_sala(
        "J-001", PERIODO_INICIO, PERIODO_FIN
    )
    assert resultado["Transición"] == {
        "subieron": 0,
        "mantuvieron": 0,
        "bajaron": 0,
    }


def test_conteos_nivel_excluye_observaciones_fuera_del_periodo(
    seeded: SqlAlchemyRelationalRepo,
) -> None:
    """La obs previa de N-001 (nivel 9, 10-may) no debe contaminar el cálculo.

    Si se incluyera, N-001 pasaría de 9 → 6 y contaría como "bajaron" en vez de
    "subieron". El resultado correcto es que sube (4 → 6).
    """
    resultado = seeded.conteos_nivel_por_sala(
        "J-001", PERIODO_INICIO, PERIODO_FIN
    )
    assert resultado["Sala Cuna"]["subieron"] == 1
    assert resultado["Sala Cuna"]["bajaron"] == 1


# ---------------------------------------------------------------------------
# 7.3 — Distribución de niveles por sala
# ---------------------------------------------------------------------------
def test_distribucion_niveles_por_sala(seeded: SqlAlchemyRelationalRepo) -> None:
    resultado = seeded.distribucion_niveles_por_sala(
        "J-001", PERIODO_INICIO, PERIODO_FIN
    )
    # Sala Cuna: niveles de O-001(4), O-002(6), O-003(5), O-004(3),
    #            O-005(4), O-006(4) → {4:3, 6:1, 5:1, 3:1}.
    # Sala Media: O-007(7) → {7:1}. (O-008 sin nivel se omite; O-009 fuera.)
    assert resultado == {
        "Sala Cuna": {3: 1, 4: 3, 5: 1, 6: 1},
        "Sala Media": {7: 1},
    }


# ---------------------------------------------------------------------------
# 7.3 — Distribución de niveles por dominio
# ---------------------------------------------------------------------------
def test_distribucion_niveles_por_dominio(
    seeded: SqlAlchemyRelationalRepo,
) -> None:
    resultado = seeded.distribucion_niveles_por_dominio(
        "J-001", PERIODO_INICIO, PERIODO_FIN
    )
    # cognitivo: O-001(nivel 4) + O-005(nivel 4) → {4: 2}.
    # socioemocional: O-002(nivel 6) → {6: 1}.
    assert resultado == {
        "cognitivo": {4: 2},
        "socioemocional": {6: 1},
    }


# ---------------------------------------------------------------------------
# 7.3 — Conteo de observaciones total y por educadora
# ---------------------------------------------------------------------------
def test_contar_observaciones_periodo(seeded: SqlAlchemyRelationalRepo) -> None:
    resultado = seeded.contar_observaciones_periodo(
        "J-001", PERIODO_INICIO, PERIODO_FIN
    )
    # Dentro del período: E-001 → O-001,O-002,O-003,O-004,O-005,O-006 = 6.
    #                     E-002 → O-007, O-008 = 2.  (O-PRE y O-009 fuera.)
    # Observa que O-008 cuenta aunque no tenga nivel (es una observación válida).
    assert resultado == {
        "total": 8,
        "por_educadora": {"E-001": 6, "E-002": 2},
    }


# ---------------------------------------------------------------------------
# 7.3 — Conteo de bitácoras total y por educadora
# ---------------------------------------------------------------------------
def test_contar_bitacoras_periodo(seeded: SqlAlchemyRelationalRepo) -> None:
    resultado = seeded.contar_bitacoras_periodo(
        "J-001", PERIODO_INICIO, PERIODO_FIN
    )
    # Dentro del período: B-001, B-002 (E-001) y B-003 (E-002). B-004 fuera.
    assert resultado == {
        "total": 3,
        "por_educadora": {"E-001": 2, "E-002": 1},
    }


# ---------------------------------------------------------------------------
# 7.3 — Alertas de retroceso
# ---------------------------------------------------------------------------
def test_alertas_retroceso(seeded: SqlAlchemyRelationalRepo) -> None:
    # Solo N-002 baja respecto de su nivel inicial del período (5 → 3).
    assert seeded.alertas_retroceso("J-001", PERIODO_INICIO, PERIODO_FIN) == [
        "N-002"
    ]


# ---------------------------------------------------------------------------
# 7.3 — Alertas de inactividad (14 días antes del fin del período)
# ---------------------------------------------------------------------------
def test_alertas_inactividad_14_dias(seeded: SqlAlchemyRelationalRepo) -> None:
    # Ventana (16-jun, 30-jun]: activos N-001(20), N-002(18), N-003(25).
    # Inactivos: N-004 (10-jun) y N-005 (03-jun).
    assert seeded.alertas_inactividad("J-001", PERIODO_FIN, dias=14) == [
        "N-004",
        "N-005",
    ]


def test_alertas_inactividad_borde_inicio_exclusivo(
    seeded: SqlAlchemyRelationalRepo,
) -> None:
    """El inicio de la ventana es exclusivo: una obs justo en el borde no activa.

    Con ``fecha_fin = 18-jun`` y 14 días, la ventana es (04-jun, 18-jun]. La
    última obs de N-003 que cae ahí es la del 05-jun → activo. Movemos el fin a
    justo el día de una observación para confirmar el extremo superior inclusivo
    y el inferior exclusivo.
    """
    # fecha_fin = 20-jun, dias = 14 → ventana (06-jun, 20-jun].
    # N-001 20-jun (incluido, extremo superior) → activo.
    # N-003 obs 05-jun y 25-jun: 05-jun queda fuera (<=06-jun exclusivo) y
    # 25-jun queda fuera (>20-jun) → N-003 inactivo en esta ventana.
    resultado = seeded.alertas_inactividad("J-001", date(2024, 6, 20), dias=14)
    assert "N-001" not in resultado  # tiene obs el 20-jun (borde superior)
    assert "N-003" in resultado  # sin obs dentro de (06-jun, 20-jun]
