"""Implementación pgvector sobre Aurora/Postgres del :class:`VectorRepo`.

Camino **primario** (Requirement 4.6): un documento por observación en una tabla
``observacion_embeddings`` de Aurora Serverless v2 con la extensión ``pgvector``.
La búsqueda semántica usa el operador de **distancia coseno** ``<=>`` de pgvector
(``similitud = 1 - distancia``), con filtros de igualdad sobre los seis metadatos
de contrato y un ``LIMIT k`` (Requirements 4.3, 4.7).

Separación de datos (Requirement 11.5): la tabla vectorial solo guarda el
seudónimo ``id_nino`` + texto/metadatos y el embedding; los datos personales
(nombre real, RUT) viven únicamente en la base relacional.

DIP: la implementación recibe una *factoría de conexiones* psycopg (callable sin
argumentos que devuelve una conexión ``with``-able). El contenedor de DI la
construye con la cadena de conexión/credenciales de Aurora (Secrets Manager);
los servicios dependen solo de la interfaz :class:`VectorRepo`.
"""

from __future__ import annotations

from typing import Any, Callable

from app.providers.errors import EmbeddingError
from app.repositories.vector.base import VectorRepo

# Nombre de la tabla vectorial (documento por observación).
TABLA = "observacion_embeddings"

# Los seis metadatos de contrato que todo documento debe transportar (Req. 4.3).
METADATOS_CONTRATO = (
    "id_observacion",
    "id_nino",
    "dominio",
    "nivel",
    "fecha",
    "formato",
)

# Columnas de metadatos filtrables (lista blanca para evitar inyección SQL en
# nombres de columna; los valores siempre van parametrizados).
_COLUMNAS_FILTRABLES = frozenset(METADATOS_CONTRATO)

ConnectionFactory = Callable[[], Any]


class PgVectorRepo(VectorRepo):
    """Repositorio vectorial respaldado por pgvector sobre Aurora/Postgres.

    Args:
        connection_factory: callable que devuelve una conexión psycopg nueva,
            usable como context manager (``with connection_factory() as conn``).
            Se inyecta (DIP) para que el contenedor de DI gestione cadena de
            conexión y credenciales, y para poder sustituirla en pruebas.
        dim: dimensión del embedding (columna ``vector(dim)``). Debe coincidir
            con la del ``EmbeddingProvider`` (Titan v2 = 1024).
    """

    def __init__(self, connection_factory: ConnectionFactory, dim: int = 1024) -> None:
        if dim <= 0:
            raise ValueError("La dimensión del embedding debe ser positiva.")
        self._connection_factory = connection_factory
        self._dim = dim

    # --- Esquema -----------------------------------------------------------
    def ensure_schema(self) -> None:
        """Crea la extensión ``pgvector`` y la tabla vectorial si no existen.

        Idempotente: puede llamarse en el arranque/seed sin efectos adversos.
        """
        try:
            from pgvector.psycopg import register_vector
        except ImportError as exc:  # pragma: no cover - entorno sin pgvector
            raise EmbeddingError(
                "El paquete 'pgvector' no está disponible para la base vectorial."
            ) from exc

        ddl = (
            "CREATE EXTENSION IF NOT EXISTS vector;",
            f"""
            CREATE TABLE IF NOT EXISTS {TABLA} (
                id_observacion TEXT PRIMARY KEY,
                id_nino        TEXT NOT NULL,
                dominio        TEXT,
                nivel          INTEGER,
                fecha          DATE,
                formato        TEXT,
                texto          TEXT,
                embedding      vector({self._dim}) NOT NULL
            );
            """,
            # Índice ANN por distancia coseno para acelerar el <=>.
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TABLA}_embedding
            ON {TABLA} USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """,
        )
        try:
            with self._connection_factory() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    for sentence in ddl:
                        cur.execute(sentence)
                conn.commit()
        except EmbeddingError:
            raise
        except Exception as exc:  # psycopg/red/permiso
            raise EmbeddingError(
                "No se pudo preparar el esquema de la base vectorial."
            ) from exc

    # --- Indexación --------------------------------------------------------
    def index(self, doc: dict[str, Any]) -> None:
        """Inserta/actualiza el documento-por-observación (UPSERT por PK).

        Indexar dos veces el mismo ``id_observacion`` deja un único registro
        vigente gracias al ``ON CONFLICT`` sobre la clave primaria.

        Raises:
            EmbeddingError: si faltan campos de contrato o si la escritura en la
                base vectorial falla (Requirement 4.4).
        """
        if not isinstance(doc, dict):
            raise EmbeddingError("El documento a indexar debe ser un dict.")

        embedding = doc.get("embedding")
        if not isinstance(embedding, (list, tuple)) or not embedding:
            raise EmbeddingError(
                "El documento a indexar debe incluir un 'embedding' no vacío."
            )
        try:
            vector = [float(component) for component in embedding]
        except (TypeError, ValueError) as exc:
            raise EmbeddingError(
                "El 'embedding' debe ser una lista de números."
            ) from exc

        faltantes = [m for m in METADATOS_CONTRATO if m not in doc]
        if faltantes:
            raise EmbeddingError(
                "El documento no incluye los metadatos de contrato: "
                + ", ".join(faltantes)
            )

        sql = f"""
            INSERT INTO {TABLA}
                (id_observacion, id_nino, dominio, nivel, fecha, formato,
                 texto, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_observacion) DO UPDATE SET
                id_nino   = EXCLUDED.id_nino,
                dominio   = EXCLUDED.dominio,
                nivel     = EXCLUDED.nivel,
                fecha     = EXCLUDED.fecha,
                formato   = EXCLUDED.formato,
                texto     = EXCLUDED.texto,
                embedding = EXCLUDED.embedding;
        """
        params = (
            doc["id_observacion"],
            doc["id_nino"],
            self._as_scalar(doc["dominio"]),
            doc["nivel"],
            doc["fecha"],
            self._as_scalar(doc["formato"]),
            doc.get("texto"),
            self._to_vector(vector),
        )
        self._run_write(sql, params)

    # --- Búsqueda ----------------------------------------------------------
    def search(
        self,
        query_embedding: list[float],
        filtros: dict[str, Any],
        k: int,
    ) -> list[dict[str, Any]]:
        """Devuelve hasta ``k`` documentos por similitud coseno descendente.

        Usa el operador de distancia coseno ``<=>`` de pgvector (menor distancia
        = mayor similitud) y aplica los ``filtros`` de igualdad como ``WHERE``
        parametrizado. Una búsqueda por ``{"id_observacion": ...}`` recupera
        exactamente ese registro con sus seis metadatos.
        """
        if k <= 0:
            return []

        filtros = filtros or {}
        where_sql, where_params = self._construir_where(filtros)
        query_vector = self._to_vector([float(c) for c in query_embedding])

        sql = f"""
            SELECT id_observacion, id_nino, dominio, nivel, fecha, formato,
                   texto, embedding
            FROM {TABLA}
            {where_sql}
            ORDER BY embedding <=> %s
            LIMIT %s;
        """
        params = [*where_params, query_vector, k]

        rows = self._run_read(sql, params)
        return [self._row_to_doc(row) for row in rows]

    # --- Utilidades internas ----------------------------------------------
    def _construir_where(
        self, filtros: dict[str, Any]
    ) -> tuple[str, list[Any]]:
        """Arma un ``WHERE`` de igualdades sobre columnas de la lista blanca.

        Raises:
            EmbeddingError: si se filtra por una columna no permitida.
        """
        clausulas: list[str] = []
        valores: list[Any] = []
        for columna, valor in filtros.items():
            if columna not in _COLUMNAS_FILTRABLES:
                raise EmbeddingError(
                    f"Filtro no permitido sobre la columna '{columna}'."
                )
            clausulas.append(f"{columna} = %s")
            valores.append(self._as_scalar(valor))
        where_sql = ("WHERE " + " AND ".join(clausulas)) if clausulas else ""
        return where_sql, valores

    def _run_write(self, sql: str, params: tuple[Any, ...]) -> None:
        """Ejecuta una escritura, registrando ``pgvector`` en la conexión."""
        try:
            from pgvector.psycopg import register_vector

            with self._connection_factory() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                conn.commit()
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                "No se pudo indexar el documento en la base vectorial."
            ) from exc

    def _run_read(self, sql: str, params: list[Any]) -> list[tuple[Any, ...]]:
        """Ejecuta una consulta de lectura y devuelve las filas crudas."""
        try:
            from pgvector.psycopg import register_vector

            with self._connection_factory() as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return list(cur.fetchall())
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                "No se pudo consultar la base vectorial."
            ) from exc

    @staticmethod
    def _to_vector(vector: list[float]) -> Any:
        """Envuelve la lista en el tipo ``Vector`` de pgvector si está presente."""
        try:
            from pgvector import Vector

            return Vector(vector)
        except ImportError:  # pragma: no cover - entorno sin pgvector
            return vector

    @staticmethod
    def _as_scalar(valor: Any) -> Any:
        """Normaliza enums de dominio a su ``value`` para almacenarlos como texto."""
        return valor.value if hasattr(valor, "value") else valor

    @staticmethod
    def _row_to_doc(row: tuple[Any, ...]) -> dict[str, Any]:
        """Mapea una fila ``SELECT`` al documento de contrato."""
        embedding = row[7]
        # pgvector devuelve numpy array / Vector; normalizar a list[float].
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        return {
            "id_observacion": row[0],
            "id_nino": row[1],
            "dominio": row[2],
            "nivel": row[3],
            "fecha": row[4],
            "formato": row[5],
            "texto": row[6],
            "embedding": [float(c) for c in embedding] if embedding is not None else None,
        }


__all__ = ["PgVectorRepo", "TABLA", "METADATOS_CONTRATO"]
