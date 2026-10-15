"""Gestión del engine y las sesiones SQLAlchemy (Capa 3).

Centraliza la creación del ``Engine`` y de la factoría de sesiones para que la
implementación relacional sea portable entre SQLite (modo demo/tests) y
Postgres/pgvector (AWS) sin cambiar el resto del código.

Para SQLite se activa ``PRAGMA foreign_keys=ON`` en cada conexión: SQLite no
aplica las claves foráneas por defecto, y queremos que la integridad
referencial del esquema E-1 se respete igual que en Postgres. Para ``:memory:``
se usa además un pool de conexión única (``StaticPool``) de modo que todas las
sesiones compartan la misma base en memoria (clave para los tests).
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.repositories.schema import Base


def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:
    """Activa la aplicación de claves foráneas en conexiones SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Crea un ``Engine`` portable para SQLite o Postgres.

    - Para SQLite se activan las claves foráneas vía ``PRAGMA``.
    - Para SQLite en memoria se usa ``StaticPool`` + ``check_same_thread=False``
      para que la base persista mientras viva el engine y sea compartible.
    """
    is_sqlite = database_url.startswith("sqlite")
    is_memory = is_sqlite and (":memory:" in database_url or database_url.endswith("://"))

    connect_args: dict = {}
    kwargs: dict = {"echo": echo, "future": True}
    if is_sqlite:
        connect_args["check_same_thread"] = False
    if is_memory:
        kwargs["poolclass"] = StaticPool

    engine = create_engine(database_url, connect_args=connect_args, **kwargs)

    if is_sqlite:
        event.listen(engine, "connect", _enable_sqlite_fk)

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Devuelve una factoría de sesiones ligada al engine dado."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def create_all(engine: Engine) -> None:
    """Crea todas las tablas del esquema relacional en el engine dado."""
    Base.metadata.create_all(engine)


def drop_all(engine: Engine) -> None:
    """Elimina todas las tablas del esquema relacional (útil en tests)."""
    Base.metadata.drop_all(engine)


__all__ = [
    "create_db_engine",
    "create_session_factory",
    "create_all",
    "drop_all",
]
