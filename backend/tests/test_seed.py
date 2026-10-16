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

import csv
import io
import json
import zipfile
from pathlib import Path

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
from app.repositories.seed.dataset_loader import CARPETA_DATOS, NOMBRE_CONSOLIDADO, TABLAS
from app.repositories.seed.seed import (
    SeedValidationError,
    cargar_distribucion_y_validacion,
    conteos_esperados,
    seed,
    seed_oficial,
    seed_rubrica_oficial,
    validar_conteos,
)
from app.repositories.seed.dataset_loader import DatasetE1

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


# ===========================================================================
# Camino OFICIAL: carga desde el zip público vía DatasetLoader + validación
# de conteos contra distribucion_y_validacion (Requirements 10.8–10.9, 14.1–14.2)
# ===========================================================================

# Filas mínimas (consistentes en FKs) para construir un dataset E-1 "oficial"
# de juguete: un jardín, una educadora, un niño, un nivel, una manifestación,
# dos observaciones (una con nivel/nota/edad ausentes) y un vínculo.
_FILAS: dict[str, list[dict[str, str]]] = {
    "jardines": [
        {
            "id_jardin": "J-001",
            "nombre_fantasia": "Los Girasoles",
            "comuna": "Maipú",
            "region": "Región Metropolitana",
            "numero_salas": "2",
            "numero_educadoras": "1",
        },
    ],
    "educadoras": [
        {
            "id_educadora": "E-001",
            "id_jardin": "J-001",
            "rol": "educadora_parvulos",
            "anios_experiencia": "4",
        },
    ],
    "ninos": [
        {
            "id_nino": "N-001",
            "id_jardin": "J-001",
            "fecha_nacimiento": "2021-03-04",
            "sexo_registrado": "M",
            "sala_grupo": "Sala Cuna",
            "fecha_ingreso": "2023-01-29",
        },
    ],
    "ruta_niveles": [
        {
            "nivel": "1",
            "nombre_nivel": "Vínculo inicial",
            "edad_min_meses": "0",
            "edad_max_meses": "8",
            "dominios": json.dumps(["cognitivo"], ensure_ascii=False),
            "descripcion": "Nivel 1 de la ruta.",
        },
    ],
    "manifestaciones": [
        {
            "id_manifestacion": "M-N1-COG-1",
            "nivel": "1",
            "dominio": "cognitivo",
            "texto_observable": "[N1] Clasifica objetos por un atributo.",
        },
    ],
    "observaciones": [
        {
            "id_observacion": "O-0001",
            "id_nino": "N-001",
            "id_educadora": "E-001",
            "fecha_observacion": "2024-03-29",
            "formato_captura": "video",
            "nivel_estimado": "4",
            "nota_breve": "Jugó en el patio.",
            "edad_meses": "36",
        },
        # Observación con nivel/nota/edad AUSENTES (celdas vacías) → Req 14.4.
        {
            "id_observacion": "O-0002",
            "id_nino": "N-001",
            "id_educadora": "E-001",
            "fecha_observacion": "2024-03-23",
            "formato_captura": "texto",
            "nivel_estimado": "",
            "nota_breve": "",
            "edad_meses": "",
        },
    ],
    "observacion_manifestaciones": [
        {"id_observacion": "O-0001", "id_manifestacion": "M-N1-COG-1"},
    ],
}

_CABECERAS: dict[str, list[str]] = {t: list(_FILAS[t][0]) for t in TABLAS}

# Conteos de referencia (distribucion_y_validacion dentro de consolidado.json).
_CONTEOS_OK = {t: len(_FILAS[t]) for t in TABLAS}


def _escribir_zip(ruta_zip: Path, conteos: dict[str, int]) -> Path:
    """Crea un ``dataset_e1_publico.zip`` de juguete con los conteos dados."""
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        for tabla in TABLAS:
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=_CABECERAS[tabla])
            writer.writeheader()
            writer.writerows(_FILAS[tabla])
            zf.writestr(f"{CARPETA_DATOS}/{tabla}.csv", buffer.getvalue())
        consolidado = {
            "semilla": 20261013,
            "fecha_referencia": "2026-10-13",
            "conteos": conteos,
        }
        zf.writestr(
            f"{CARPETA_DATOS}/{NOMBRE_CONSOLIDADO}",
            json.dumps(consolidado, ensure_ascii=False),
        )
    return ruta_zip


@pytest.fixture()
def zip_oficial(tmp_path: Path) -> Path:
    """Zip oficial de juguete con conteos de referencia correctos."""
    return _escribir_zip(tmp_path / "dataset_e1_publico.zip", dict(_CONTEOS_OK))


def test_seed_oficial_carga_desde_zip_y_valida_conteos(
    repo, session_factory, zip_oficial
) -> None:
    """``seed_oficial`` carga las 7 tablas desde el zip y valida conteos OK.

    Además siembra la versión inicial de la rúbrica oficial (su fuente es el PDF
    transcrito, no el zip): el resumen incluye ``rubrica_versiones`` junto a las
    7 tablas del dataset oficial (tarea 7.3).
    """
    cargados = seed_oficial(repo, zip_oficial)
    assert {t: cargados[t] for t in TABLAS} == _CONTEOS_OK
    assert cargados["rubrica_versiones"] >= 1
    # Las filas quedaron realmente en la base relacional.
    assert _contar(session_factory, Jardin) == 1
    assert _contar(session_factory, Observacion) == 2
    assert _contar(session_factory, ObservacionManifestacion) == 1
    assert _contar(session_factory, RubricaVersion) >= 1


def test_seed_oficial_carga_roles_reales_del_dataset(
    repo, session_factory, tmp_path
) -> None:
    """Los valores de ``rol`` del Dataset E-1 oficial se cargan sin error.

    La columna ``rol`` del ``educadoras.csv`` oficial trae exactamente dos
    valores de aula —``educadora_parvulos`` y ``tecnico_parvulos``— más
    ``directora``. El enum ``Rol`` del dominio/esquema debe aceptarlos tal cual
    (la fuente de verdad es el dataset). Este test construye un zip oficial de
    juguete con esos tres valores y verifica que persisten intactos.
    """
    filas = {tabla: [dict(f) for f in _FILAS[tabla]] for tabla in TABLAS}
    filas["jardines"][0]["numero_educadoras"] = "3"
    filas["educadoras"] = [
        {"id_educadora": "E-001", "id_jardin": "J-001",
         "rol": "educadora_parvulos", "anios_experiencia": "4"},
        {"id_educadora": "E-002", "id_jardin": "J-001",
         "rol": "tecnico_parvulos", "anios_experiencia": "9"},
        {"id_educadora": "E-003", "id_jardin": "J-001",
         "rol": "directora", "anios_experiencia": "15"},
    ]
    conteos = {t: len(filas[t]) for t in TABLAS}

    ruta = tmp_path / "dataset_e1_publico.zip"
    with zipfile.ZipFile(ruta, "w") as zf:
        for tabla in TABLAS:
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=list(filas[tabla][0]))
            writer.writeheader()
            writer.writerows(filas[tabla])
            zf.writestr(f"{CARPETA_DATOS}/{tabla}.csv", buffer.getvalue())
        zf.writestr(
            f"{CARPETA_DATOS}/{NOMBRE_CONSOLIDADO}",
            json.dumps({"conteos": conteos}, ensure_ascii=False),
        )

    cargados = seed_oficial(repo, ruta)
    assert cargados["educadoras"] == 3

    with session_factory() as session:
        roles = {
            e.id_educadora: (e.rol.value if hasattr(e.rol, "value") else str(e.rol))
            for e in session.execute(select(Educadora)).scalars().all()
        }
    assert roles == {
        "E-001": "educadora_parvulos",
        "E-002": "tecnico_parvulos",
        "E-003": "directora",
    }


def test_seed_oficial_mapea_celdas_vacias_como_ausencia(
    repo, session_factory, zip_oficial
) -> None:
    """Nota/nivel/edad ausentes (celdas vacías) se cargan como NULL (Req 14.4)."""
    seed_oficial(repo, zip_oficial)
    with session_factory() as session:
        obs = session.get(Observacion, "O-0002")
        assert obs is not None
        assert obs.nivel_estimado is None
        assert obs.edad_meses is None
        assert obs.nota_breve is None


def test_seed_oficial_es_idempotente(repo, session_factory, zip_oficial) -> None:
    """Cargar el dataset oficial dos veces no duplica filas (merge por PK)."""
    primera = seed_oficial(repo, zip_oficial)
    seed_oficial(repo, zip_oficial)
    assert _contar(session_factory, Observacion) == 2
    assert _contar(session_factory, Nino) == 1
    # La rúbrica tampoco se duplica entre ejecuciones (merge por version_rubrica).
    assert _contar(session_factory, RubricaVersion) == primera["rubrica_versiones"]


def test_seed_oficial_rechaza_si_un_conteo_no_coincide(
    repo, tmp_path
) -> None:
    """Si distribucion_y_validacion no cuadra, se rechaza con error en español."""
    # El consolidado dice que debería haber 5 observaciones, pero el CSV trae 2.
    conteos_malos = dict(_CONTEOS_OK, observaciones=5)
    ruta = _escribir_zip(tmp_path / "dataset_e1_publico.zip", conteos_malos)
    with pytest.raises(SeedValidationError) as exc:
        seed_oficial(repo, ruta)
    mensaje = str(exc.value)
    assert "conteos" in mensaje.lower()
    assert "observaciones" in mensaje
    assert "se esperaban 5" in mensaje


def test_validar_conteos_ok() -> None:
    """``validar_conteos`` no lanza si todos los conteos coinciden."""
    validar_conteos({"ninos": 500, "jardines": 2}, {"ninos": 500, "jardines": 2})


def test_validar_conteos_detecta_discrepancia() -> None:
    """``validar_conteos`` lanza un error en español ante una discrepancia."""
    with pytest.raises(SeedValidationError, match="no coinciden"):
        validar_conteos({"ninos": 499}, {"ninos": 500})


def test_validar_conteos_detecta_tabla_faltante() -> None:
    """Una tabla sin filas cargadas pero esperada también es discrepancia."""
    with pytest.raises(SeedValidationError, match="ninguna fila"):
        validar_conteos({}, {"ninos": 500})


def test_conteos_esperados_desde_consolidado() -> None:
    """Compat. hacia atrás: usa la sección 'conteos' plana si está presente."""
    dataset = DatasetE1(csvs={}, consolidado={"conteos": dict(_CONTEOS_OK)})
    esperados = conteos_esperados(dataset)
    assert esperados == _CONTEOS_OK


def test_conteos_esperados_consolidado_oficial_sin_conteos() -> None:
    """Dataset E-1 oficial (consolidado anidado, SIN 'conteos') valida OK.

    El ``consolidado.json`` oficial no trae un bloque plano ``conteos`` (sus
    claves son ``fecha_referencia``, ``jardines``, ``naturaleza``,
    ``ruta_niveles``, ``schema_version``). ``conteos_esperados`` debe derivar
    los conteos del propio CSV y, si las listas anidadas del consolidado
    cuadran, no debe lanzar.
    """
    csvs = {tabla: list(_FILAS[tabla]) for tabla in TABLAS}
    consolidado_oficial = {
        "fecha_referencia": "2026-10-13",
        "schema_version": "1.0.0",
        "naturaleza": "sintetico",
        # Listas anidadas coherentes con los CSV (1 jardín, 1 nivel de ruta).
        "jardines": [{"id_jardin": "J-001"}],
        "ruta_niveles": [{"nivel": 1}],
    }
    dataset = DatasetE1(csvs=csvs, consolidado=consolidado_oficial)
    esperados = conteos_esperados(dataset)
    # Los conteos esperados se derivan del CSV (consistencia interna).
    assert esperados == {tabla: len(_FILAS[tabla]) for tabla in TABLAS}


def test_conteos_esperados_rechaza_consolidado_anidado_incoherente() -> None:
    """Si las listas anidadas del consolidado no cuadran con los CSV, se rechaza."""
    csvs = {tabla: list(_FILAS[tabla]) for tabla in TABLAS}
    # El CSV trae 1 jardín, pero el consolidado dice 3: incoherencia interna.
    consolidado_incoherente = {
        "fecha_referencia": "2026-10-13",
        "jardines": [{"id_jardin": "J-001"}, {"id_jardin": "J-002"}, {"id": "J-003"}],
        "ruta_niveles": [{"nivel": 1}],
    }
    dataset = DatasetE1(csvs=csvs, consolidado=consolidado_incoherente)
    with pytest.raises(SeedValidationError) as exc:
        conteos_esperados(dataset)
    mensaje = str(exc.value)
    assert "jardines" in mensaje
    assert "incoherente" in mensaje.lower()


def test_seed_oficial_oficial_sin_conteos_valida_y_detecta_mismatch(
    repo, session_factory, tmp_path
) -> None:
    """Un zip con consolidado estilo oficial (sin 'conteos') seedea OK.

    Y si se simula un descarte de fila (consolidado anidado que no cuadra con el
    CSV) el seed debe rechazar con ``SeedValidationError`` en español.
    """
    # 1) Zip estilo oficial: consolidado anidado coherente, SIN clave 'conteos'.
    ruta_ok = tmp_path / "dataset_oficial_ok.zip"
    with zipfile.ZipFile(ruta_ok, "w") as zf:
        for tabla in TABLAS:
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=_CABECERAS[tabla])
            writer.writeheader()
            writer.writerows(_FILAS[tabla])
            zf.writestr(f"{CARPETA_DATOS}/{tabla}.csv", buffer.getvalue())
        consolidado = {
            "fecha_referencia": "2026-10-13",
            "schema_version": "1.0.0",
            "jardines": [{"id_jardin": "J-001"}],
            "ruta_niveles": [{"nivel": 1}],
        }
        zf.writestr(
            f"{CARPETA_DATOS}/{NOMBRE_CONSOLIDADO}",
            json.dumps(consolidado, ensure_ascii=False),
        )
    cargados = seed_oficial(repo, ruta_ok)
    assert {t: cargados[t] for t in TABLAS} == _CONTEOS_OK
    assert _contar(session_factory, Observacion) == 2

    # 2) Zip incoherente: el consolidado dice 9 ruta_niveles pero el CSV trae 1.
    ruta_mal = tmp_path / "dataset_oficial_mal.zip"
    with zipfile.ZipFile(ruta_mal, "w") as zf:
        for tabla in TABLAS:
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=_CABECERAS[tabla])
            writer.writeheader()
            writer.writerows(_FILAS[tabla])
            zf.writestr(f"{CARPETA_DATOS}/{tabla}.csv", buffer.getvalue())
        consolidado_mal = {
            "fecha_referencia": "2026-10-13",
            "jardines": [{"id_jardin": "J-001"}],
            "ruta_niveles": [{"nivel": n} for n in range(1, 10)],  # 9 ≠ 1 CSV
        }
        zf.writestr(
            f"{CARPETA_DATOS}/{NOMBRE_CONSOLIDADO}",
            json.dumps(consolidado_mal, ensure_ascii=False),
        )
    with pytest.raises(SeedValidationError) as exc:
        seed_oficial(repo, ruta_mal)
    assert "ruta_niveles" in str(exc.value)


# ===========================================================================
# Tarea 7.3 — Siembra de la versión inicial de la rúbrica oficial en
# ``rubrica_versiones`` vía la interfaz ``RelationalRepo`` (Req 6.6, 21.1, 21.5)
# ===========================================================================

# Los 3 tramos de sala y el orden fijo de los 8 niveles de progresión que la
# rúbrica oficial debe traer para el núcleo "identidad_y_autonomia".
_TRAMOS = ("sala_cuna", "nivel_medio", "transicion")
_NIVELES_ESPERADOS = [
    (1, "Comenzando"),
    (2, "Explorando"),
    (3, "Desarrollando"),
    (4, "Afianzando"),
    (5, "Integrando"),
    (6, "Ampliando"),
    (7, "Consolidando"),
    (8, "Profundizando"),
]
# Rangos etarios (en meses) por tramo, según el diseño.
_RANGOS_ETARIOS = {
    "sala_cuna": [0, 24],
    "nivel_medio": [24, 48],
    "transicion": [48, 72],
}


def _rubrica_vigente_criterios(repo) -> dict:
    """Devuelve los ``criterios`` de la rúbrica vigente sembrada vía el repo."""
    vigente = repo.rubrica_vigente()
    assert vigente is not None, "No se sembró ninguna versión de rúbrica."
    assert isinstance(vigente.criterios, dict)
    return vigente.criterios


def test_seed_rubrica_oficial_persiste_version_via_repo(repo, session_factory) -> None:
    """``seed_rubrica_oficial`` siembra ≥1 versión y queda consultable por el repo."""
    n = seed_rubrica_oficial(repo)
    assert n >= 1
    assert _contar(session_factory, RubricaVersion) == n
    # Se accede a la rúbrica solo vía la interfaz del repo (no vía SDK).
    vigente = repo.rubrica_vigente()
    assert vigente is not None
    assert vigente.version_rubrica


def test_rubrica_contiene_nucleo_identidad_en_los_3_tramos(repo) -> None:
    """La versión sembrada trae el núcleo Identidad y Autonomía en los 3 tramos."""
    seed_rubrica_oficial(repo)
    criterios = _rubrica_vigente_criterios(repo)
    tramos = criterios["tramos"]
    for tramo in _TRAMOS:
        assert tramo in tramos, f"Falta el tramo '{tramo}'."
        assert tramos[tramo]["rango_etario_meses"] == _RANGOS_ETARIOS[tramo]
        nucleos = tramos[tramo]["nucleos"]
        assert "identidad_y_autonomia" in nucleos, (
            f"Falta el núcleo identidad_y_autonomia en el tramo '{tramo}'."
        )


def test_cada_tramo_tiene_8_niveles_en_orden_correcto(repo) -> None:
    """Cada tramo×núcleo trae exactamente los 8 niveles de progresión en orden."""
    seed_rubrica_oficial(repo)
    criterios = _rubrica_vigente_criterios(repo)
    for tramo in _TRAMOS:
        niveles = criterios["tramos"][tramo]["nucleos"]["identidad_y_autonomia"][
            "niveles"
        ]
        assert len(niveles) == 8, f"El tramo '{tramo}' no tiene 8 niveles."
        pares = [(int(nv["n"]), nv["nombre"]) for nv in niveles]
        assert pares == _NIVELES_ESPERADOS, (
            f"Los niveles del tramo '{tramo}' no están en el orden esperado."
        )


def test_cada_nivel_tiene_descriptor_y_conductas_observables(repo) -> None:
    """Cada nivel trae un descriptor no vacío y ≥1 conducta observable."""
    seed_rubrica_oficial(repo)
    criterios = _rubrica_vigente_criterios(repo)
    for tramo in _TRAMOS:
        niveles = criterios["tramos"][tramo]["nucleos"]["identidad_y_autonomia"][
            "niveles"
        ]
        for nivel in niveles:
            assert isinstance(nivel.get("descriptor"), str)
            assert nivel["descriptor"].strip(), (
                f"Descriptor vacío en {tramo} nivel {nivel['n']}."
            )
            conductas = nivel.get("conductas_observables")
            assert isinstance(conductas, list) and conductas, (
                f"Sin conductas observables en {tramo} nivel {nivel['n']}."
            )
            assert all(isinstance(c, str) and c.strip() for c in conductas)


def test_rubrica_define_umbrales_de_decision(repo) -> None:
    """La rúbrica trae los umbrales de decisión versionados (Req 21.5)."""
    seed_rubrica_oficial(repo)
    criterios = _rubrica_vigente_criterios(repo)
    umbrales = criterios["umbrales"]
    assert "cobertura_avanzar" in umbrales
    assert "nucleos_requeridos" in umbrales
    assert "racha_retroceso" in umbrales
    assert "identidad_y_autonomia" in umbrales["nucleos_requeridos"]


def test_seed_rubrica_oficial_es_idempotente(repo, session_factory) -> None:
    """Re-ejecutar la siembra no crea versiones duplicadas (merge por PK)."""
    primera = seed_rubrica_oficial(repo)
    segunda = seed_rubrica_oficial(repo)
    assert primera == segunda
    assert _contar(session_factory, RubricaVersion) == primera


def test_seed_reducido_tambien_siembra_la_rubrica(repo, session_factory) -> None:
    """El camino de seed reducido deja la rúbrica consultable vía el repo."""
    resumen = seed(repo)
    assert resumen["rubrica_versiones"] >= 1
    assert _contar(session_factory, RubricaVersion) == resumen["rubrica_versiones"]
    assert repo.rubrica_vigente() is not None
