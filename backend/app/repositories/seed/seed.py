"""Script de seed del dataset E-1 en la base relacional (Requirement 10.2).

Carga los archivos JSON generados bajo ``seed/data/`` en las tablas del esquema
relacional. El seed es **idempotente**: usa ``RelationalRepo.add_all`` (que
hace ``merge`` por clave primaria), de modo que ejecutarlo dos veces no duplica
filas ni rompe las claves foráneas.

Alcance de esta tarea (3.3): se carga la **base relacional**. El sembrado de la
base vectorial (embeddings) queda como punto de extensión claro para las tareas
4.x, y la orquestación completa del seed (relacional + vectorial) para la tarea
17. La función :func:`seed` recibe un ``RelationalRepo`` ya construido, por lo
que el llamador decide el motor (SQLite demo / Postgres AWS).

Entrada ejecutable::

    python -m app.repositories.seed.seed

que usa la ``DATABASE_URL`` configurada en ``core`` (Settings) para crear el
engine, las tablas y poblarlas.

El orden de inserción respeta las dependencias de claves foráneas:
``jardines`` → ``educadoras``/``ninos`` → ``ruta_niveles`` →
``manifestaciones`` → ``observaciones`` → ``observacion_manifestaciones``;
``rubrica_versiones`` es independiente.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

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


def _load_json(tabla: str) -> list[dict]:
    """Lee el archivo JSON de una tabla del dataset."""
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
    """Carga en memoria todas las tablas del dataset E-1 desde los JSON."""
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
    """Carga el dataset E-1 en la base relacional vía ``repo``.

    Es idempotente: ``add_all`` fusiona por clave primaria, así que una segunda
    ejecución no duplica filas. Devuelve el conteo de filas insertadas por
    tabla (según el dataset de origen), útil para log/verificación.

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


def _seed_desde_settings() -> dict[str, int]:  # pragma: no cover - entrypoint
    """Construye engine/repo desde Settings y ejecuta el seed (entrypoint)."""
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

    resumen = seed(repo)
    total = sum(resumen.values())
    print(f"Seed E-1 completado en {settings.database_url}")
    for tabla, n in resumen.items():
        print(f"  {tabla}: {n}")
    print(f"  TOTAL filas: {total}")
    return resumen


if __name__ == "__main__":  # pragma: no cover
    _seed_desde_settings()


__all__ = [
    "seed",
    "cargar_dataset",
    "cargar_distribucion_y_validacion",
    "DISTRIBUCION_Y_VALIDACION",
    "DATA_DIR",
    "SEED_ORDER",
]
