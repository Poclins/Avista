"""Implementación en memoria del :class:`VectorRepo` (camino secundario).

Índice vectorial sin dependencias externas para CI/local (``USE_MOCKS=true``),
intercambiable (LSP) con la implementación pgvector sobre Aurora (Requirement
4.6). Guarda un documento por ``id_observacion`` en un ``dict`` y calcula la
similitud **coseno** en Python puro, de modo que las pruebas de recuperación
semántica del Módulo C corran sin Postgres ni credenciales.

Contrato de documento (Requirement 4.3): cada documento lleva el ``embedding``
(``list[float]``) y los seis metadatos de contrato (``id_observacion``,
``id_nino``, ``dominio``, ``nivel``, ``fecha``, ``formato``), más el texto
transcrito asociado. Indexar dos veces el mismo ``id_observacion`` deja un único
registro vigente (reemplazo). Una búsqueda por ``{"id_observacion": ...}``
recupera exactamente ese registro con sus seis metadatos.

Privacidad (Requirement 11.5): el índice vectorial solo almacena el seudónimo
``id_nino`` + texto/metadatos; nunca nombre real ni RUT, que viven únicamente en
la base relacional.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from app.providers.errors import EmbeddingError
from app.repositories.vector.base import VectorRepo

# Los seis metadatos de contrato que todo documento debe transportar (Req. 4.3).
METADATOS_CONTRATO = (
    "id_observacion",
    "id_nino",
    "dominio",
    "nivel",
    "fecha",
    "formato",
)


class InMemoryVectorRepo(VectorRepo):
    """Índice vectorial en memoria con similitud coseno (camino secundario)."""

    def __init__(self) -> None:
        # id_observacion -> documento (copia defensiva del indexado).
        self._docs: dict[Any, dict[str, Any]] = {}

    # --- Indexación --------------------------------------------------------
    def index(self, doc: dict[str, Any]) -> None:
        """Indexa (o reemplaza) un documento-por-observación.

        Raises:
            EmbeddingError: si falta el ``embedding`` o alguno de los seis
                metadatos de contrato, o si el embedding no es un vector de
                números (Requirement 4.4).
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

        id_observacion = doc["id_observacion"]
        # Copia defensiva con el embedding normalizado a list[float] para que el
        # registro vigente no dependa de mutaciones externas del documento.
        stored = deepcopy(doc)
        stored["embedding"] = vector
        self._docs[id_observacion] = stored

    # --- Búsqueda ----------------------------------------------------------
    def search(
        self,
        query_embedding: list[float],
        filtros: dict[str, Any],
        k: int,
    ) -> list[dict[str, Any]]:
        """Devuelve hasta ``k`` documentos por similitud coseno descendente.

        Los ``filtros`` son de igualdad sobre los metadatos; solo los documentos
        que los cumplen todos entran en el ranking. Una búsqueda por
        ``{"id_observacion": ...}`` recupera exactamente ese registro.
        """
        if k <= 0:
            return []

        filtros = filtros or {}
        candidatos = [
            doc for doc in self._docs.values() if self._cumple_filtros(doc, filtros)
        ]

        query = [float(component) for component in query_embedding]
        clasificados = sorted(
            candidatos,
            key=lambda doc: self._similitud_coseno(query, doc["embedding"]),
            reverse=True,
        )

        # Copia defensiva para que el llamador no mute el índice.
        return [deepcopy(doc) for doc in clasificados[:k]]

    # --- Utilidades internas ----------------------------------------------
    @staticmethod
    def _cumple_filtros(doc: dict[str, Any], filtros: dict[str, Any]) -> bool:
        """``True`` si el documento satisface todos los filtros de igualdad."""
        return all(doc.get(clave) == valor for clave, valor in filtros.items())

    @staticmethod
    def _similitud_coseno(a: list[float], b: list[float]) -> float:
        """Similitud coseno entre dos vectores; 0.0 si alguno es nulo."""
        producto = sum(x * y for x, y in zip(a, b))
        norma_a = math.sqrt(sum(x * x for x in a))
        norma_b = math.sqrt(sum(y * y for y in b))
        if norma_a == 0.0 or norma_b == 0.0:
            return 0.0
        return producto / (norma_a * norma_b)


__all__ = ["InMemoryVectorRepo", "METADATOS_CONTRATO"]
