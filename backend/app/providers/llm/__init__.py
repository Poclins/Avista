"""Puerto LLM (Bedrock/Claude): interfaz + adaptadores AWS/mock.

- ``LlmProvider``: interfaz (puerto) del Módulo A.
- ``BedrockLlmProvider``: adaptador **primario** (Amazon Bedrock, Claude).
- ``MockLlmProvider``: adaptador **secundario** (local/CI) que deriva texto
  plausible en español de forma determinista, sin red.
- ``GuardedLlmProvider``: decorador transversal que aplica el resguardo de datos
  sensibles (despersonalización) antes de delegar en el proveedor activo
  (Requirements 11.2, 11.3).

La selección entre AWS y mock la realiza el contenedor de DI según ``USE_MOCKS``;
el contenedor envuelve el proveedor elegido con ``GuardedLlmProvider`` para que
todos los caminos de invocación al LLM queden protegidos.
"""

from app.providers.llm.base import LlmProvider
from app.providers.llm.bedrock_llm import BedrockLlmProvider
from app.providers.llm.guarded_llm import GuardedLlmProvider
from app.providers.llm.mock_llm import MockLlmProvider

__all__ = [
    "LlmProvider",
    "BedrockLlmProvider",
    "MockLlmProvider",
    "GuardedLlmProvider",
]
