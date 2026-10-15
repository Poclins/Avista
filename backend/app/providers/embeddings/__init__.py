"""Puerto de embeddings (Titan): interfaz + adaptadores AWS/mock."""

from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.mock_embeddings import MockEmbeddingProvider
from app.providers.embeddings.titan_embeddings import TitanEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "MockEmbeddingProvider",
    "TitanEmbeddingProvider",
]
