"""Tests del ``DatasetLoader`` del Dataset E-1 oficial (tarea 3.7).

Verifican la lectura de los **7 CSV relacionales** + ``consolidado.json`` y el
**mapeo de cada fila a las entidades ORM** del dominio (Módulo A), tanto desde
un directorio como desde el **zip público** ``dataset_e1_publico.zip``.

Como el zip oficial completo (500 niños) no se versiona en el repositorio, los
tests generan **fixtures CSV mínimas** que ejercitan el casteo de tipos, el
mapeo a entidades ORM y el manejo de celdas vacías como **ausencia de dato**
(nota/nivel/edad ausentes), sin depender de ningún artefacto externo.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date
from pathlib import Path

import pytest

from app.repositories.schema import (
    Educadora,
    Jardin,
    Manifestacion,
    Nino,
    Observacion,
    ObservacionManifestacion,
    RutaNivel,
)
from app.repositories.seed.dataset_loader import (
    CARPETA_DATOS,
    NOMBRE_CONSOLIDADO,
    TABLAS,
    DatasetLoader,
    DatasetLoaderError,
)

def _enum_value(valor: object) -> object:
    """Valor del enum, aceptando enum o la cadena cruda (ORM sin flush)."""
    return valor.value if hasattr(valor, "value") else valor


# --------------------------------------------------------------------------
# Datos de fixture (una o dos filas por tabla) como filas de texto CSV.
# Las columnas coinciden 1:1 con el esquema ORM del dataset E-1.
# --------------------------------------------------------------------------
FILAS: dict[str, list[dict[str, str]]] = {
    "jardines": [
        {
            "id_jardin": "J-001",
            "nombre_fantasia": "Los Girasoles",
            "comuna": "Maipú",
            "region": "Región Metropolitana",
            "numero_salas": "2",
            "numero_educadoras": "3",
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
            "dominios": json.dumps(
                ["cognitivo", "socioemocional"], ensure_ascii=False
            ),
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
        # Observación completa: nivel y nota presentes.
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
        # Observación con nivel/nota/edad AUSENTES (celdas vacías).
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

# Columnas (cabecera CSV) por tabla, en orden estable.
CABECERAS: dict[str, list[str]] = {tabla: list(FILAS[tabla][0]) for tabla in TABLAS}

CONSOLIDADO = {
    "semilla": 20261013,
    "fecha_referencia": "2026-10-13",
    "conteos": {tabla: len(FILAS[tabla]) for tabla in TABLAS},
}


def _escribir_csv(path: Path, tabla: str) -> None:
    """Escribe un CSV UTF-8/LF con la cabecera y filas de la tabla."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CABECERAS[tabla])
        writer.writeheader()
        writer.writerows(FILAS[tabla])


@pytest.fixture()
def directorio_dataset(tmp_path: Path) -> Path:
    """Crea un directorio con los 7 CSV + consolidado.json de fixture."""
    for tabla in TABLAS:
        _escribir_csv(tmp_path / f"{tabla}.csv", tabla)
    (tmp_path / NOMBRE_CONSOLIDADO).write_text(
        json.dumps(CONSOLIDADO, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture()
def zip_dataset(tmp_path: Path) -> Path:
    """Crea un ``dataset_e1_publico.zip`` con la carpeta ``datos_publicos/``."""
    ruta_zip = tmp_path / "dataset_e1_publico.zip"
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        for tabla in TABLAS:
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=CABECERAS[tabla])
            writer.writeheader()
            writer.writerows(FILAS[tabla])
            zf.writestr(f"{CARPETA_DATOS}/{tabla}.csv", buffer.getvalue())
        zf.writestr(
            f"{CARPETA_DATOS}/{NOMBRE_CONSOLIDADO}",
            json.dumps(CONSOLIDADO, ensure_ascii=False),
        )
    return ruta_zip


# --------------------------------------------------------------------------
# read_csvs / read_consolidado
# --------------------------------------------------------------------------
def test_read_csvs_lee_las_7_tablas(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    csvs = loader.read_csvs()
    assert set(csvs) == set(TABLAS)
    # Las filas son dicts de texto con las columnas del esquema.
    assert csvs["jardines"][0]["id_jardin"] == "J-001"
    assert len(csvs["observaciones"]) == 2


def test_read_csvs_falla_si_falta_un_csv(directorio_dataset: Path) -> None:
    (directorio_dataset / "ninos.csv").unlink()
    loader = DatasetLoader(directorio_dataset)
    with pytest.raises(DatasetLoaderError, match="ninos.csv"):
        loader.read_csvs()


def test_read_consolidado(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    consolidado = loader.read_consolidado()
    assert consolidado["semilla"] == 20261013
    assert consolidado["fecha_referencia"] == "2026-10-13"


def test_read_consolidado_falla_si_falta(directorio_dataset: Path) -> None:
    (directorio_dataset / NOMBRE_CONSOLIDADO).unlink()
    loader = DatasetLoader(directorio_dataset)
    with pytest.raises(DatasetLoaderError, match=NOMBRE_CONSOLIDADO):
        loader.read_consolidado()


# --------------------------------------------------------------------------
# to_entities: mapeo de filas → entidades ORM del dominio A
# --------------------------------------------------------------------------
def test_to_entities_mapea_jardin(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    (jardin,) = loader.to_entities("jardines", FILAS["jardines"])
    assert isinstance(jardin, Jardin)
    assert jardin.id_jardin == "J-001"
    assert jardin.numero_salas == 2  # casteado a int
    assert jardin.numero_educadoras == 3


def test_to_entities_castea_fechas_de_nino(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    (nino,) = loader.to_entities("ninos", FILAS["ninos"])
    assert isinstance(nino, Nino)
    assert nino.fecha_nacimiento == date(2021, 3, 4)
    assert nino.fecha_ingreso == date(2023, 1, 29)


def test_to_entities_castea_lista_de_dominios(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    (nivel,) = loader.to_entities("ruta_niveles", FILAS["ruta_niveles"])
    assert isinstance(nivel, RutaNivel)
    assert nivel.nivel == 1
    assert nivel.dominios == ["cognitivo", "socioemocional"]


def test_to_entities_manifestacion(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    (m,) = loader.to_entities("manifestaciones", FILAS["manifestaciones"])
    assert isinstance(m, Manifestacion)
    assert m.nivel == 1
    assert _enum_value(m.dominio) == "cognitivo"


def test_to_entities_observacion_completa(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    obs = loader.to_entities("observaciones", FILAS["observaciones"])
    primera = obs[0]
    assert isinstance(primera, Observacion)
    assert primera.fecha_observacion == date(2024, 3, 29)
    assert _enum_value(primera.formato_captura) == "video"
    assert primera.nivel_estimado == 4
    assert primera.edad_meses == 36
    assert primera.nota_breve == "Jugó en el patio."


def test_to_entities_observacion_con_campos_ausentes(directorio_dataset: Path) -> None:
    """Celdas vacías = ausencia de dato (None), no dato inválido (Req 14.4)."""
    loader = DatasetLoader(directorio_dataset)
    obs = loader.to_entities("observaciones", FILAS["observaciones"])
    segunda = obs[1]
    assert segunda.id_observacion == "O-0002"
    assert segunda.nivel_estimado is None
    assert segunda.edad_meses is None
    assert segunda.nota_breve is None


def test_to_entities_vinculo_observacion_manifestacion(
    directorio_dataset: Path,
) -> None:
    loader = DatasetLoader(directorio_dataset)
    (vinculo,) = loader.to_entities(
        "observacion_manifestaciones", FILAS["observacion_manifestaciones"]
    )
    assert isinstance(vinculo, ObservacionManifestacion)
    assert vinculo.id_observacion == "O-0001"
    assert vinculo.id_manifestacion == "M-N1-COG-1"


def test_to_entities_tabla_desconocida(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    with pytest.raises(DatasetLoaderError, match="desconocida"):
        loader.to_entities("inexistente", [])


def test_to_entities_valor_no_casteable(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    fila_mala = [dict(FILAS["jardines"][0], numero_salas="dos")]
    with pytest.raises(DatasetLoaderError, match="jardines"):
        loader.to_entities("jardines", fila_mala)


def test_entidades_por_tabla_mapea_todo_en_orden(directorio_dataset: Path) -> None:
    loader = DatasetLoader(directorio_dataset)
    entidades = loader.entidades_por_tabla()
    assert list(entidades) == list(TABLAS)  # orden canónico
    assert all(len(entidades[t]) == len(FILAS[t]) for t in TABLAS)
    assert isinstance(entidades["jardines"][0], Jardin)
    assert isinstance(entidades["educadoras"][0], Educadora)


# --------------------------------------------------------------------------
# load(): ruta primaria desde el zip público
# --------------------------------------------------------------------------
def test_load_desde_zip_publico(zip_dataset: Path) -> None:
    dataset = DatasetLoader.load(zip_dataset)
    assert set(dataset.csvs) == set(TABLAS)
    assert dataset.consolidado["semilla"] == 20261013
    assert dataset.csvs["ninos"][0]["id_nino"] == "N-001"


def test_load_zip_inexistente() -> None:
    with pytest.raises(DatasetLoaderError, match="No se encontró el zip"):
        DatasetLoader.load("no_existe.zip")


def test_load_zip_sin_consolidado(tmp_path: Path) -> None:
    ruta_zip = tmp_path / "incompleto.zip"
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        for tabla in TABLAS:
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=CABECERAS[tabla])
            writer.writeheader()
            writer.writerows(FILAS[tabla])
            zf.writestr(f"{CARPETA_DATOS}/{tabla}.csv", buffer.getvalue())
    with pytest.raises(DatasetLoaderError, match=NOMBRE_CONSOLIDADO):
        DatasetLoader.load(ruta_zip)


def test_load_zip_sin_un_csv(tmp_path: Path) -> None:
    ruta_zip = tmp_path / "falta_csv.zip"
    with zipfile.ZipFile(ruta_zip, "w") as zf:
        for tabla in TABLAS:
            if tabla == "educadoras":
                continue  # omitimos un CSV a propósito
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=CABECERAS[tabla])
            writer.writeheader()
            writer.writerows(FILAS[tabla])
            zf.writestr(f"{CARPETA_DATOS}/{tabla}.csv", buffer.getvalue())
        zf.writestr(
            f"{CARPETA_DATOS}/{NOMBRE_CONSOLIDADO}", json.dumps(CONSOLIDADO)
        )
    with pytest.raises(DatasetLoaderError, match="educadoras.csv"):
        DatasetLoader.load(ruta_zip)


def test_load_mapea_a_entidades_orm(zip_dataset: Path) -> None:
    """De punta a punta: zip → DatasetE1 → entidades ORM via to_entities."""
    dataset = DatasetLoader.load(zip_dataset)
    loader = DatasetLoader(zip_dataset.parent)  # dir sólo para la API de mapeo
    jardines = loader.to_entities("jardines", dataset.csvs["jardines"])
    assert isinstance(jardines[0], Jardin)
    assert jardines[0].id_jardin == "J-001"
