"""Repositorio vectorial (Capa 3): interfaz + adaptadores pgvector/memoria.

- Primario (AWS): :class:`PgVectorRepo` sobre Aurora Serverless v2 (pgvector).
- Secundario (CI/local): :class:`InMemoryVectorRepo`, índice en memoria.

Ambos implementan la interfaz congelada :class:`VectorRepo` y son
intercambiables (LSP), seleccionados por ``USE_MOCKS`` en el contenedor de DI.
"""

from app.repositories.vector.base import VectorRepo
from app.repositories.vector.memory_vector_repo import InMemoryVectorRepo
from app.repositories.vector.pgvector_repo import PgVectorRepo

__all__ = ["VectorRepo", "InMemoryVectorRepo", "PgVectorRepo"]
