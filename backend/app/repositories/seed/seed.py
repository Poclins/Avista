"""Script de seed del Dataset E-1 en la base relacional (Requirements 10.8–10.9, 14.1–14.2).

Fuente de verdad (**Dataset E-1 oficial**): el seed carga el **zip público**
``dataset_e1_publico.zip`` (siete CSV relacionales + ``consolidado.json``) a
través de :class:`~app.repositories.seed.dataset_loader.DatasetLoader`, que
queda **encapsulado detrás de la frontera del seed**: el llamador solo conoce
la interfaz ``RelationalRepo``, de modo que cambiar de dataset (oficial ↔
reducido casero) **no toca el código de los servicios**.

Tras cargar, el seed **valida los conteos** cargados contra
``distribucion_y_validacion`` (los conteos de referencia que vienen en
``consolidado.json``) y **rechaza la carga con un error en español**
(:class:`SeedValidationError`) si algún conteo no coincide (Requirement 10.9 /
14.2). La carga procesa los 500 niños/as sin error, incluidas las
observaciones con nota/formato/manifestación ausente (celda vacía = ausencia de
registro, no dato inválido — Requirement 14.4), que ``DatasetLoader`` ya mapea
a ``None``.

Respaldo rápido de pruebas (**dataset reducido/casero**): se conserva la carga
"un JSON por tabla" bajo ``seed/data/`` vía :func:`seed`, usada **solo** como
respaldo veloz de pruebas, nunca como fuente de verdad (Requirement 10.11).

El seed es **idempotente**: usa ``RelationalRepo.add_all`` (que hace ``merge``
por clave primaria), de modo que ejecutarlo dos veces no duplica filas ni rompe
las claves foráneas.

Entrada ejecutable::

    python -m app.repositories.seed.seed

que usa ``DATABASE_URL`` y ``DATASET_ZIP_PATH`` de ``core`` (Settings): si el
zip oficial existe, carga el Dataset E-1 oficial con validación de conteos; si
no, cae al dataset reducido con un aviso.

El orden de inserción respeta las dependencias de claves foráneas:
``jardines`` → ``educadoras``/``ninos`` → ``ruta_niveles`` →
``manifestaciones`` → ``observaciones`` → ``observacion_manifestaciones``;
``rubrica_versiones`` es independiente.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from app.repositories.relational.base import RelationalRepo
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
from app.repositories.seed.dataset_loader import (
    TABLAS,
    DatasetE1,
    DatasetLoader,
    DatasetLoaderError,
)

DATA_DIR = Path(__file__).parent / "data"

# Orden de carga: respeta las dependencias de claves foráneas.
SEED_ORDER: list[tuple[str, type[Base]]] = [
    ("jardines", Jardin),
    ("educadoras", Educadora),
    ("ninos", Nino),
    ("ruta_niveles", RutaNivel),
    ("manifestaciones", Manifestacion),
    ("observaciones", Observacion),
    ("observacion_manifestaciones", ObservacionManifestacion),
    ("rubrica_versiones", RubricaVersion),
]

# Campos que deben convertirse de ISO string a ``date`` al construir las ORM.
_DATE_FIELDS: dict[type[Base], tuple[str, ...]] = {
    Nino: ("fecha_nacimiento", "fecha_ingreso"),
    Observacion: ("fecha_observacion",),
    RubricaVersion: ("vigente_desde",),
}


class SeedError(ValueError):
    """Error (en español) del proceso de seed del Dataset E-1 oficial."""


class SeedValidationError(SeedError):
    """La validación de conteos del seed falló: algún conteo no coincide.

    Se lanza cuando los conteos realmente cargados no cuadran con los valores
    de referencia de ``distribucion_y_validacion`` (Requirement 10.9 / 14.2).
    """


# ===========================================================================
# Camino OFICIAL: carga del zip público vía DatasetLoader + validación
# ===========================================================================
def conteos_esperados(dataset: DatasetE1) -> dict[str, int]:
    """Extrae los conteos de referencia de ``distribucion_y_validacion``.

    Los conteos esperados por tabla vienen en ``consolidado.json`` bajo la
    clave ``conteos`` (la sección de ``distribucion_y_validacion`` del dataset
    oficial). Se devuelve ``{tabla: n_esperado}`` para las 7 tablas relacionales
    presentes en el dataset.

    Raises:
        SeedValidationError: si ``consolidado.json`` no trae la sección de
            conteos de referencia (no se puede validar la carga).
    """
    conteos = dataset.consolidado.get("conteos")
    if not isinstance(conteos, dict):
        raise SeedValidationError(
            "El 'consolidado.json' del Dataset E-1 no contiene la sección de "
            "conteos de referencia ('conteos' en 'distribucion_y_validacion'); "
            "no es posible validar la carga."
        )
    esperados: dict[str, int] = {}
    for tabla in TABLAS:
        if tabla in conteos:
            esperados[tabla] = int(conteos[tabla])
    return esperados


def validar_conteos(
    cargados: dict[str, int], esperados: dict[str, int]
) -> None:
    """Valida que los conteos cargados coincidan con los de referencia.

    Compara, tabla por tabla, el número de filas realmente cargado contra el
    valor de referencia de ``distribucion_y_validacion``. Si algún conteo no
    coincide, **rechaza la carga con un error en español** detallando cada
    discrepancia (Requirement 10.9 / 14.2).

    Args:
        cargados: ``{tabla: n_cargado}`` del dataset efectivamente insertado.
        esperados: ``{tabla: n_esperado}`` de ``distribucion_y_validacion``.

    Raises:
        SeedValidationError: si alguna tabla no coincide (o falta un conteo).
    """
    discrepancias: list[str] = []
    for tabla, n_esperado in esperados.items():
        n_cargado = cargados.get(tabla)
        if n_cargado is None:
            discrepancias.append(
                f"- tabla '{tabla}': no se cargó ninguna fila, "
                f"se esperaban {n_esperado}."
            )
        elif n_cargado != n_esperado:
            discrepancias.append(
                f"- tabla '{tabla}': se cargaron {n_cargado} filas, "
                f"se esperaban {n_esperado}."
            )

    if discrepancias:
        detalle = "\n".join(discrepancias)
        raise SeedValidationError(
            "Validación de conteos del Dataset E-1 fallida: los conteos "
            "cargados no coinciden con 'distribucion_y_validacion'.\n"
            f"{detalle}"
        )


def seed_oficial(
    repo: RelationalRepo, ruta_zip: str | Path
) -> dict[str, int]:
    """Carga el **Dataset E-1 oficial** desde el zip público y valida conteos.

    Lee ``dataset_e1_publico.zip`` vía :meth:`DatasetLoader.load`, mapea cada
    fila a entidades ORM del dominio (Módulo A) con ``to_entities`` y las
    inserta en la base relacional vía ``repo`` respetando el orden de claves
    foráneas. Al terminar, **valida los conteos cargados** contra
    ``distribucion_y_validacion`` y **rechaza con error en español** si alguno
    no coincide (Requirement 10.9 / 14.2).

    `DatasetLoader` queda encapsulado tras esta frontera del seed: el resto del
    sistema solo conoce ``RelationalRepo``.

    Args:
        repo: repositorio relacional ya construido (SQLite demo o Postgres AWS).
        ruta_zip: ruta al ``dataset_e1_publico.zip`` (zip público oficial).

    Returns:
        Diccionario ``{tabla: n_filas}`` de las 7 tablas cargadas.

    Raises:
        DatasetLoaderError: si el zip no existe o está incompleto/corrupto.
        SeedValidationError: si algún conteo cargado no coincide con la
            distribución de referencia.
    """
    dataset = DatasetLoader.load(ruta_zip)
    loader = DatasetLoader(Path(ruta_zip).parent)  # solo para to_entities

    cargados: dict[str, int] = {}
    for tabla in TABLAS:
        filas = dataset.csvs.get(tabla, [])
        entidades = loader.to_entities(tabla, filas)
        if entidades:
            repo.add_all(entidades)
        cargados[tabla] = len(entidades)

    # Validación de conteos contra distribucion_y_validacion (consolidado.json).
    validar_conteos(cargados, conteos_esperados(dataset))
    return cargados


# ===========================================================================
# Camino de RESPALDO: dataset reducido/casero ("un JSON por tabla")
# ===========================================================================
def _load_json(tabla: str) -> list[dict]:
    """Lee el archivo JSON de una tabla del dataset reducido (respaldo)."""
    path = DATA_DIR / f"{tabla}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _to_entity(model: type[Base], fila: dict) -> Base:
    """Construye una entidad ORM desde una fila del JSON (parsea fechas)."""
    datos = dict(fila)
    for campo in _DATE_FIELDS.get(model, ()):  # type: ignore[arg-type]
        valor = datos.get(campo)
        if isinstance(valor, str):
            datos[campo] = date.fromisoformat(valor)
    return model(**datos)


def cargar_dataset() -> dict[str, list[dict]]:
    """Carga en memoria todas las tablas del dataset reducido desde los JSON."""
    return {tabla: _load_json(tabla) for tabla, _ in SEED_ORDER}


def cargar_distribucion_y_validacion() -> dict:
    """Carga el archivo ``distribucion_y_validacion.json`` (conteos esperados)."""
    path = DATA_DIR / "distribucion_y_validacion.json"
    return json.loads(path.read_text(encoding="utf-8"))


def __getattr__(name: str):
    """Carga perezosa de ``DISTRIBUCION_Y_VALIDACION``.

    Evita leer el JSON al importar el módulo (p. ej. durante la generación del
    propio dataset, cuando los archivos aún no existen). PEP 562.
    """
    if name == "DISTRIBUCION_Y_VALIDACION":
        return cargar_distribucion_y_validacion()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def seed(repo: RelationalRepo) -> dict[str, int]:
    """Carga el dataset reducido/casero en la base relacional vía ``repo``.

    Respaldo rápido de pruebas (Requirement 10.11): carga los JSON por tabla de
    ``seed/data/``. Es idempotente: ``add_all`` fusiona por clave primaria, así
    que una segunda ejecución no duplica filas. Devuelve el conteo de filas
    insertadas por tabla.

    Para la carga de la **fuente de verdad** (Dataset E-1 oficial) use
    :func:`seed_oficial`.

    Args:
        repo: repositorio relacional ya construido (SQLite demo o Postgres AWS).

    Returns:
        Diccionario ``{tabla: n_filas}`` del dataset cargado.
    """
    resumen: dict[str, int] = {}
    for tabla, model in SEED_ORDER:
        filas = _load_json(tabla)
        entidades: list[Base] = [_to_entity(model, fila) for fila in filas]
        if entidades:
            repo.add_all(entidades)
        resumen[tabla] = len(entidades)
    return resumen


# ===========================================================================
# Entrypoint ejecutable
# ===========================================================================
def _seed_desde_settings() -> dict[str, int]:  # pragma: no cover - entrypoint
    """Construye engine/repo desde Settings y ejecuta el seed (entrypoint).

    Prefiere el **Dataset E-1 oficial** (``DATASET_ZIP_PATH``) si el zip existe;
    si no, cae al dataset reducido/casero como respaldo de pruebas con un aviso.
    """
    from app.core.config import get_settings
    from app.repositories.db import (
        create_all,
        create_db_engine,
        create_session_factory,
    )
    from app.repositories.relational.sqlalchemy_repo import (
        SqlAlchemyRelationalRepo,
    )

    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    create_all(engine)
    session_factory = create_session_factory(engine)
    repo = SqlAlchemyRelationalRepo(session_factory)

    ruta_zip = Path(settings.dataset_zip_path)
    if ruta_zip.is_file():
        resumen = seed_oficial(repo, ruta_zip)
        origen = f"Dataset E-1 oficial ({ruta_zip})"
    else:
        print(
            f"[seed] Aviso: no se encontró el zip oficial en {ruta_zip}; "
            "se usa el dataset reducido/casero (solo respaldo de pruebas)."
        )
        resumen = seed(repo)
        origen = "dataset reducido/casero (respaldo)"

    total = sum(resumen.values())
    print(f"Seed completado en {settings.database_url} — origen: {origen}")
    for tabla, n in resumen.items():
        print(f"  {tabla}: {n}")
    print(f"  TOTAL filas: {total}")
    return resumen


if __name__ == "__main__":  # pragma: no cover
    _seed_desde_settings()


__all__ = [
    "seed",
    "seed_oficial",
    "conteos_esperados",
    "validar_conteos",
    "cargar_dataset",
    "cargar_distribucion_y_validacion",
    "DISTRIBUCION_Y_VALIDACION",
    "SeedError",
    "SeedValidationError",
    "DatasetLoaderError",
    "DATA_DIR",
    "SEED_ORDER",
]
