"""Handler Lambda de *seed* de Aurora para jAImes (Módulo H, tarea 11.3).

Aurora vive en subredes **privadas aisladas** (sin NAT ni acceso público), por
lo que no es posible sembrarla desde la máquina local. Este handler se despliega
como una **Lambda dedicada de seed** en la *misma* VPC/subredes/SG que la Lambda
del API (ver ``infra/stacks/compute_stack.py``) y con lectura del mismo secreto
de credenciales de Aurora. Un **custom resource** de CDK lo invoca **una vez** en
el deploy para dejar la base poblada.

Reutiliza el **mismo asset de backend** y la misma lógica que el entrypoint
``python -m app.repositories.seed.seed``:

1. Resuelve la URL de Aurora desde Secrets Manager (``Settings.resolve_database_url``).
2. Crea el esquema relacional (``create_all``) y, en Postgres, la extensión
   ``pgvector`` + la tabla vectorial (``PgVectorRepo.ensure_schema``).
3. Siembra el Dataset E-1: oficial (zip público) si está presente, o el dataset
   reducido/casero como respaldo, validando conteos.

Devuelve un resumen ``{tabla: n_filas}`` que el custom resource registra en
CloudWatch (Requirement 10.6).

Es **idempotente** (el seed usa ``merge`` por PK; el esquema usa ``IF NOT
EXISTS``), de modo que reinvocarlo no duplica filas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Nombre del evento que distingue una invocación de custom resource de CFN de
# una invocación directa (p. ej. prueba manual con la consola/CLI).
_CFN_REQUEST_TYPES = {"Create", "Update", "Delete"}


def _ejecutar_seed() -> dict[str, int]:
    """Prepara el esquema (relacional + pgvector) y siembra el Dataset E-1.

    Reutiliza la resolución perezosa de la URL de BD del contenedor de DI (que
    arma la URL de Aurora desde el secreto) y la lógica de seed compartida con
    el entrypoint de línea de comandos.
    """
    import os

    from app.core.config import get_settings
    from app.repositories.db import (
        create_all,
        create_db_engine,
        create_session_factory,
        drop_all,
    )
    from app.repositories.relational.sqlalchemy_repo import (
        SqlAlchemyRelationalRepo,
    )
    from app.repositories.seed.seed import seed, seed_oficial

    settings = get_settings()
    url = settings.resolve_database_url()

    # Diagnóstico (Requirement 10.6): deja rastro en CloudWatch de qué dataset
    # ve el handler, para distinguir "zip oficial no encontrado" de un fallo de
    # mapeo/validación cuando los conteos no cuadran.
    ruta_zip_dbg = settings.dataset_zip_path
    print(
        f"[seed] dataset_zip_path={ruta_zip_dbg!r} "
        f"isfile={os.path.isfile(ruta_zip_dbg)}"
    )

    es_postgres = url.startswith("postgresql")

    # 1) Esquema relacional.
    engine = create_db_engine(url)

    # 1a) MIGRACIÓN DE ESQUEMA (solo Postgres/Aurora, nunca SQLite):
    #     en un re-deploy, el tipo enum ``rol`` ya existe en Aurora con valores
    #     antiguos; ``create_all`` NO altera tipos existentes, así que el seed
    #     fallaría de nuevo al insertar un valor nuevo del enum. Reconstruimos
    #     el esquema desde cero: ``drop_all`` elimina las tablas y, como los
    #     tipos ENUM de Postgres pueden quedar huérfanos, forzamos un
    #     ``DROP TYPE IF EXISTS ... CASCADE`` explícito antes de recrear. Todo
    #     es idempotente y seguro de re-ejecutar (Aurora conserva los datos vía
    #     removal_policy; el seed vuelve a poblar). En SQLite no aplica (los
    #     enums se mapean a texto con CHECK y ``create_all`` basta).
    if es_postgres:
        drop_all(engine)
        _eliminar_tipos_enum_postgres(url)

    create_all(engine)

    # 2) Extensión pgvector + tabla vectorial (solo en Postgres/Aurora).
    #    En SQLite (demo/local) se omite: no hay 'CREATE EXTENSION'.
    if es_postgres:
        _preparar_pgvector(url, settings)

    # 3) Seed: oficial (zip público) si existe, o reducido como respaldo.
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

    print(f"[seed] Seed completado — origen: {origen}")
    for tabla, n in resumen.items():
        print(f"[seed]   {tabla}: {n}")
    print(f"[seed]   TOTAL filas: {sum(resumen.values())}")
    return resumen


def _preparar_pgvector(url: str, settings: Any) -> None:
    """Crea la extensión ``vector`` y la tabla vectorial en Aurora (idempotente).

    Importante: en una base **recién creada** la extensión ``vector`` aún no
    existe, y ``pgvector.psycopg.register_vector`` falla si el tipo ``vector`` no
    está registrado en el servidor. Por eso aquí se ejecuta primero
    ``CREATE EXTENSION IF NOT EXISTS vector`` en una conexión **sin**
    ``register_vector`` (bootstrap de la extensión) y recién después se delega en
    ``PgVectorRepo.ensure_schema`` (que ya puede registrar el tipo y crear la
    tabla/índice vectorial). La dimensión coincide con la del
    ``EmbeddingProvider`` (Titan v2 = 1024).
    """
    import psycopg

    from app.providers.embeddings.titan_embeddings import (
        DEFAULT_DIMENSION as _TITAN_DIM,
    )
    from app.repositories.vector.pgvector_repo import PgVectorRepo

    # ``psycopg.connect`` espera una URL libpq (``postgresql://``), no la URL
    # de dialecto SQLAlchemy (``postgresql+psycopg://``).
    libpq_url = url.replace("postgresql+psycopg://", "postgresql://", 1)

    def _factory():
        return psycopg.connect(libpq_url)

    # 1) Bootstrap de la extensión pgvector (sin register_vector): deja el tipo
    #    'vector' disponible en el servidor antes de que nadie lo registre.
    with _factory() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()

    # 2) Tabla + índice vectorial vía el mismo camino que producción.
    PgVectorRepo(_factory, dim=_TITAN_DIM).ensure_schema()


# Tipos ENUM nativos de Postgres creados por el esquema relacional
# (``SAEnum(..., name=...)`` en ``app.repositories.schema``). Al reconstruir el
# esquema hay que eliminarlos explícitamente: ``Base.metadata.drop_all`` borra
# las tablas pero puede dejar estos tipos huérfanos, y entonces ``create_all``
# no los recrea con los valores nuevos (p. ej. los nuevos valores de ``rol``).
_TIPOS_ENUM_POSTGRES: tuple[str, ...] = (
    "rol",
    "dominio",
    "formato_captura",
    "estado_bitacora",
    "decision_nivel",
)


def _eliminar_tipos_enum_postgres(url: str) -> None:
    """Elimina los tipos ENUM nativos de Postgres (idempotente, solo Postgres).

    Tras ``drop_all`` las tablas desaparecen, pero los tipos ``CREATE TYPE ...
    AS ENUM`` que SQLAlchemy generó pueden quedar en el catálogo con los
    **valores antiguos**. Como un re-deploy debe reconstruir el enum ``rol`` con
    los valores reales del dataset (``educadora_parvulos`` / ``tecnico_parvulos``
    / ``directora``), aquí forzamos ``DROP TYPE IF EXISTS <t> CASCADE`` para cada
    tipo conocido. ``IF EXISTS`` lo hace seguro de re-ejecutar; ``CASCADE`` cubre
    cualquier dependencia residual.
    """
    import psycopg

    libpq_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(libpq_url) as conn:
        with conn.cursor() as cur:
            for tipo in _TIPOS_ENUM_POSTGRES:
                cur.execute(f'DROP TYPE IF EXISTS "{tipo}" CASCADE;')
        conn.commit()


def handler(event: Any = None, context: Any = None) -> dict[str, Any]:
    """Entrypoint Lambda del seed.

    Soporta dos modos de invocación:

    - **Directa** (consola/CLI): ejecuta el seed y devuelve
      ``{"ok": True, "resumen": {...}}``.
    - **Custom resource de CloudFormation** (vía el *provider framework* de CDK,
      ``custom_resources.Provider``): el evento trae ``RequestType``. En
      ``Create``/``Update`` ejecuta el seed; en ``Delete`` no hace nada (el seed
      es idempotente y los datos los gestiona Aurora vía ``removal_policy``). El
      *provider framework* envía la respuesta a CloudFormation según este
      handler **retorne** (éxito) o **lance** (fallo), por lo que aquí NO se usa
      ``cfnresponse`` manualmente. Un fallo propaga la excepción para que el
      deploy reporte el problema y quede reintentar-able.

    El ``PhysicalResourceId`` se mantiene estable entre ``Create`` y ``Update``
    para que CloudFormation no dispare un ``Delete`` del recurso anterior.
    """
    try:
        request_type = (event or {}).get("RequestType")
    except AttributeError:
        request_type = None

    # --- Invocación directa (no es un custom resource de CFN) --------------
    if request_type not in _CFN_REQUEST_TYPES:
        resumen = _ejecutar_seed()
        return {"ok": True, "resumen": resumen}

    # --- Custom resource de CloudFormation (provider framework de CDK) -----
    physical_id = "JaimesSeedAurora"
    resumen: dict[str, int] = {}
    if request_type in {"Create", "Update"}:
        resumen = _ejecutar_seed()
    # En 'Delete' no se borra nada (idempotente; datos gestionados por Aurora).
    return {
        "PhysicalResourceId": physical_id,
        "Data": {
            "filas": str(sum(resumen.values())),
            **{k: str(v) for k, v in resumen.items()},
        },
    }
