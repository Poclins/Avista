"""Interfaz del proveedor LLM (puerto de la Capa 2).

Define el contrato que los servicios de redacción (``BitacoraService``,
``RecommendationService``, ``DirectorReportService``) usan para generar texto en
español a partir de un prompt y un contexto, sin acoplarse a ningún SDK
(Requirements 5.3, 5.10, principio DIP). La implementación primaria invoca
Amazon Bedrock (Claude); la secundaria (mock) deriva texto plausible para
CI/local.

Importante: en la recomendación de nivel el LLM **solo argumenta** citando las
conductas observables y la evidencia; nunca altera la decisión determinista de
la rúbrica (Requirements 6.2, 6.7). Son intercambiables (LSP) y se seleccionan
por la configuración ``USE_MOCKS``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LlmProvider(ABC):
    """Puerto de generación de texto con un LLM.

    Las implementaciones AWS (Bedrock/Claude, primaria) y mock (secundaria) deben
    ser intercambiables: el comportamiento observable no depende del proveedor.
    """

    @abstractmethod
    def generate(self, prompt: str, context: str) -> str:
        """Genera texto en español a partir del prompt y el contexto dados.

        Args:
            prompt: instrucción de la tarea (p. ej. redactar una bitácora o el
                argumento de una recomendación).
            context: contexto fundamentante (evidencia recuperada vía RAG,
                conductas observables, rúbrica vigente, métricas agregadas).

        Returns:
            El texto generado por el modelo.

        Raises:
            LlmError: si la invocación al LLM falla o excede su plazo máximo
                (Requirements 5.4, 6.11).
        """


__all__ = ["LlmProvider"]
