"""Adaptador mock del :class:`EmbeddingProvider` (camino secundario).

Deriva un vector denso **determinista** a partir del texto, sin dependencias de
AWS, para CI/local (``USE_MOCKS=true``). El contrato clave es la reproducibilidad:
un mismo texto produce siempre el mismo vector (misma dimensión y mismos
valores), de modo que las pruebas de recuperación semántica del Módulo C sean
estables sin credenciales (Requirements 4.2, 4.5).

El determinismo se construye con ``hashlib.sha256`` (estable entre procesos y
ejecuciones, a diferencia de ``hash()`` que usa aleatorización de semilla),
expandiendo el digest hasta cubrir la dimensión pedida y normalizando los bytes
a ``float`` en el rango [-1, 1]. El vector resultante se normaliza a norma L2
unitaria para que la similitud coseno sea equivalente al producto punto.
"""

from __future__ import annotations

import hashlib
import math

from app.providers.embeddings.base import EmbeddingProvider
from app.providers.errors import EmbeddingError

# Dimensión por defecto: coincide con amazon.titan-embed-text-v2:0, para que el
# mock y el adaptador real sean intercambiables sin reindexar (LSP, Req. 4.5).
DEFAULT_DIMENSION = 1024


class MockEmbeddingProvider(EmbeddingProvider):
    """Proveedor de embeddings determinista y sin red para CI/local.

    Args:
        dimension: longitud del vector generado. Debe ser positiva. Por defecto
            coincide con la dimensión de Titan v2 (1024) para intercambiabilidad.
    """

    def __init__(self, dimension: int = DEFAULT_DIMENSION) -> None:
        if dimension <= 0:
            raise ValueError("La dimensión del embedding debe ser positiva.")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        """Dimensión estable del vector que produce este proveedor."""
        return self._dimension

    def embed(self, text: str) -> list[float]:
        """Deriva un vector determinista del texto (mismo texto ⇒ mismo vector)."""
        if not text or not text.strip():
            raise EmbeddingError("El texto a embeber no puede estar vacío.")

        raw = self._raw_vector(text)
        return self._normalize_l2(raw)

    def _raw_vector(self, text: str) -> list[float]:
        """Expande el digest SHA-256 del texto hasta cubrir la dimensión.

        Cada bloque de 32 bytes proviene de ``sha256(f"{i}:{text}")``, de modo
        que distintos textos divergen en todo el vector y el mismo texto siempre
        reproduce los mismos bytes.
        """
        encoded = text.encode("utf-8")
        values: list[float] = []
        counter = 0
        while len(values) < self._dimension:
            digest = hashlib.sha256(f"{counter}:".encode("utf-8") + encoded).digest()
            for byte in digest:
                if len(values) >= self._dimension:
                    break
                # Mapear 0..255 -> [-1, 1].
                values.append((byte / 255.0) * 2.0 - 1.0)
            counter += 1
        return values

    @staticmethod
    def _normalize_l2(vector: list[float]) -> list[float]:
        """Normaliza a norma L2 unitaria; deja el vector intacto si es nulo."""
        norm = math.sqrt(sum(component * component for component in vector))
        if norm == 0.0:
            return vector
        return [component / norm for component in vector]


__all__ = ["MockEmbeddingProvider", "DEFAULT_DIMENSION"]
