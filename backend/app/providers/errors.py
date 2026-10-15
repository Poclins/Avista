"""Excepciones tipadas de los puertos de IA (contrato del Módulo A).

Las implementaciones concretas (AWS primaria, mock secundaria) traducen sus
fallos a estas excepciones de dominio, de modo que los servicios y la capa de
API dependan de un contrato estable y no de los errores crudos de cada SDK
(Requirements 2.7, 5.4, 4.4, 13.2). La capa G las traduce a respuestas HTTP en
español sin filtrar detalles sensibles (Requirement 10.6).

Jerarquía:
- ``ProviderError`` — raíz común de todos los fallos de proveedores.
  - ``TranscriptionError`` — fallo del ``TranscriptionProvider`` (Modelo 1).
  - ``EmbeddingError`` — fallo del ``EmbeddingProvider`` (Titan).
  - ``LlmError`` — fallo del ``LlmProvider`` (Bedrock/Claude).
"""

from __future__ import annotations


class ProviderError(Exception):
    """Error base de cualquier proveedor de IA tras su interfaz."""


class TranscriptionError(ProviderError):
    """Fallo al transcribir o extraer texto de un medio (Requirement 2.7)."""


class EmbeddingError(ProviderError):
    """Fallo al generar o indexar un embedding de texto (Requirement 4.4)."""


class LlmError(ProviderError):
    """Fallo al generar texto con el LLM (Requirements 5.4, 6.11)."""


__all__ = [
    "ProviderError",
    "TranscriptionError",
    "EmbeddingError",
    "LlmError",
]
