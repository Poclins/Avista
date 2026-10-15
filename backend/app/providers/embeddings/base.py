"""Interfaz del proveedor de embeddings (puerto de la Capa 2).

Define el contrato que el ``EmbeddingService`` (Módulo C) usa para convertir el
texto de una observación en un vector denso, sin acoplarse a ningún SDK
(Requirements 4.2, 4.5, principio DIP). La implementación primaria invoca Amazon
Titan vía Bedrock; la secundaria (mock) deriva vectores deterministas del texto
para CI/local. Son intercambiables (LSP) y se seleccionan por ``USE_MOCKS``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Puerto de generación de embeddings de texto.

    Las implementaciones AWS (Titan, primaria) y mock (secundaria) deben ser
    intercambiables: al seleccionar una, todas las operaciones de embedding se
    dirigen solo a esa implementación (Requirement 4.5).
    """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Genera el embedding del texto dado.

        Args:
            text: texto no vacío a embeber (p. ej. el texto transcrito de una
                observación).

        Returns:
            El vector de embedding como lista de ``float``. Para una misma
            implementación, la dimensión es estable entre llamadas.

        Raises:
            EmbeddingError: si la generación del embedding falla (Requirement 4.4).
        """


__all__ = ["EmbeddingProvider"]
