"""Interfaz del repositorio vectorial (puerto de la Capa 3).

Define el contrato que el ``EmbeddingService`` y los servicios RAG
(``BitacoraService``, ``RecommendationService``) usan para indexar embeddings de
observaciones y recuperarlos por similitud semántica, sin acoplarse al motor
subyacente (Requirement 4.7, principio DIP). La implementación primaria usa
pgvector sobre Aurora Serverless v2 (búsqueda por similitud **coseno**); la
secundaria usa un índice en memoria tras la misma interfaz (Requirement 4.6).

Un documento por observación lleva los metadatos ``id_observacion``,
``id_nino``, ``dominio``, ``nivel``, ``fecha`` y ``formato``, de forma que una
búsqueda posterior por ``id_observacion`` recupere exactamente un registro con
esos seis metadatos (Requirement 4.3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VectorRepo(ABC):
    """Puerto de acceso a la base vectorial (índice de embeddings).

    Las implementaciones (pgvector primaria, índice en memoria secundaria) deben
    ser intercambiables (LSP): el comportamiento observable no depende del motor.
    """

    @abstractmethod
    def index(self, doc: dict[str, Any]) -> None:
        """Indexa un documento-por-observación con su embedding y metadatos.

        Args:
            doc: documento con, al menos, el ``embedding`` (``list[float]``) y
                los seis metadatos de contrato (``id_observacion``, ``id_nino``,
                ``dominio``, ``nivel``, ``fecha``, ``formato``), más el texto
                transcrito asociado. Indexar dos veces el mismo
                ``id_observacion`` deja un único registro vigente.

        Raises:
            EmbeddingError: si la indexación en la base vectorial falla
                (Requirement 4.4).
        """

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        filtros: dict[str, Any],
        k: int,
    ) -> list[dict[str, Any]]:
        """Busca los documentos más similares al embedding de consulta.

        Args:
            query_embedding: vector de consulta.
            filtros: filtros de igualdad sobre los metadatos (p. ej.
                ``{"id_nino": "N-001"}`` o un rango de fecha para la ventana del
                período) que acotan el espacio de búsqueda.
            k: número máximo de vecinos a devolver.

        Returns:
            Hasta ``k`` documentos ordenados por similitud **coseno**
            descendente, cada uno con sus metadatos de contrato. Una búsqueda
            por ``{"id_observacion": ...}`` recupera exactamente un registro con
            los seis metadatos (Requirement 4.3).
        """


__all__ = ["VectorRepo"]
