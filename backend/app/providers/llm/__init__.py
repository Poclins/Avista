"""Puerto LLM (Bedrock/Claude): interfaz + adaptadores AWS/mock.

- ``LlmProvider``: interfaz (puerto) del Módulo A.
- ``BedrockLlmProvider``: adaptador **primario** (Amazon Bedrock, Claude).
- ``MockLlmProvider``: adaptador **secundario** (local/CI) que deriva texto
  plausible en español de forma determinista, sin red.

La selección entre AWS y mock la realiza el contenedor de DI según ``USE_MOCKS``.
"""

from app.providers.llm.base import LlmProvider
from app.providers.llm.bedrock_llm import BedrockLlmProvider
from app.providers.llm.mock_llm import MockLlmProvider

__all__ = ["LlmProvider", "BedrockLlmProvider", "MockLlmProvider"]
