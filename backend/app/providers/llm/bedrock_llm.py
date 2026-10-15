"""Adaptador **AWS** del ``LlmProvider`` (primario): Amazon Bedrock (Claude).

Invoca un modelo Claude de Amazon Bedrock a través del cliente boto3
``bedrock-runtime`` para generar texto en español a partir de un ``prompt`` y un
``context`` (Requirements 5.3, 5.10), detrás de la misma interfaz que consume el
Módulo F. Es intercambiable con el mock bajo ``USE_MOCKS`` (LSP).

Robustez (Requirements 5.4, 6.11): cualquier fallo del SDK (credenciales,
servicio, cuotas) o un **timeout** se traducen a la excepción tipada
:class:`LlmError` del Módulo A, con mensaje en español y sin filtrar los
detalles crudos del SDK, para que los servicios y la Capa G respondan con un
error controlado (503) en lugar de propagar errores de AWS.

Diseño verificable en aislamiento: el cliente boto3 ``bedrock-runtime`` se
**inyecta** por el constructor; en los tests se pasa un doble de prueba y nunca
se llama a AWS real. Si no se inyecta, se crea de forma perezosa con la región,
el ``model_id`` y el timeout de la configuración (camino de producción,
``USE_MOCKS=false``).

La invocación usa la **Messages API** de Anthropic sobre Bedrock
(``invoke_model``), que es el formato que esperan los modelos Claude 3 (p. ej.
``anthropic.claude-3-haiku-20240307-v1:0``, el valor por defecto de la
configuración).
"""

from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider

# Versión de la Messages API de Anthropic en Bedrock.
_ANTHROPIC_VERSION = "bedrock-2023-05-31"

# Tope de tokens de la respuesta y temperatura por defecto (redacción sobria,
# fundamentada en la evidencia, no creativa).
_MAX_TOKENS = 1024
_TEMPERATURA = 0.2

# Instrucción de sistema: fuerza que el modelo responda en español (es-CL) y se
# ciña al contexto proporcionado (RAG), sin inventar evidencia.
_SISTEMA_ES = (
    "Eres un asistente pedagógico que redacta en español de Chile. "
    "Responde siempre en español, de forma clara y profesional, "
    "fundamentando cada afirmación únicamente en el contexto entregado."
)


class BedrockLlmProvider(LlmProvider):
    """Implementación AWS (primaria) e intercambiable del puerto LLM.

    El cliente boto3 solo se crea de forma perezosa en el camino real, por lo que
    importar o instanciar este adaptador no exige credenciales ni red.
    """

    def __init__(
        self,
        *,
        region: str | None = None,
        model_id: str | None = None,
        timeout_segundos: float | None = None,
        max_tokens: int = _MAX_TOKENS,
        temperatura: float = _TEMPERATURA,
        bedrock_runtime_client: Any | None = None,
    ) -> None:
        settings = get_settings()
        self._region = region or settings.aws_region
        self._model_id = model_id or settings.bedrock_model_id
        # Plazo máximo de la invocación; por encima de él se traduce a LlmError
        # (Requirements 5.4, 6.11). Configurable; por defecto 60 s (bitácora).
        self._timeout = (
            timeout_segundos
            if timeout_segundos is not None
            else float(getattr(settings, "llm_timeout_segundos", 60.0))
        )
        self._max_tokens = max_tokens
        self._temperatura = temperatura
        self._client = bedrock_runtime_client

    # -- Fábrica perezosa del cliente (solo en el camino real) ---------------
    def _runtime(self) -> Any:
        if self._client is not None:
            return self._client
        import boto3  # import diferido: solo necesario en producción.
        from botocore.config import Config

        # El timeout del LLM se aplica a la lectura/conexión del cliente boto3,
        # de modo que una invocación lenta se aborte y se traduzca a LlmError.
        config = Config(
            region_name=self._region,
            read_timeout=self._timeout,
            connect_timeout=min(self._timeout, 10.0),
            retries={"max_attempts": 0},
        )
        self._client = boto3.client("bedrock-runtime", config=config)
        return self._client

    # -- Generación ----------------------------------------------------------
    def generate(self, prompt: str, context: str) -> str:
        """Genera texto en español invocando Claude en Bedrock.

        Raises:
            LlmError: si la invocación falla o excede el plazo máximo
                (Requirements 5.4, 6.11), con mensaje en español.
        """
        cuerpo = self._construir_cuerpo(prompt, context)
        try:
            respuesta = self._runtime().invoke_model(
                modelId=self._model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(cuerpo),
            )
            crudo = respuesta["body"].read()
            return self._extraer_texto(crudo)
        except LlmError:
            raise
        except Exception as exc:  # fallos del SDK, timeouts, cuotas, parseo
            raise LlmError(
                "No se pudo generar el texto con el modelo de lenguaje "
                "(fallo o tiempo de espera agotado del proveedor)."
            ) from exc

    # -- Formato de la petición (Messages API de Anthropic) ------------------
    def _construir_cuerpo(self, prompt: str, context: str) -> dict[str, Any]:
        """Arma el cuerpo JSON que espera un modelo Claude 3 en Bedrock."""
        contenido_usuario = (
            f"Contexto fundamentante:\n{context}\n\n"
            f"Instrucción:\n{prompt}"
        )
        return {
            "anthropic_version": _ANTHROPIC_VERSION,
            "max_tokens": self._max_tokens,
            "temperature": self._temperatura,
            "system": _SISTEMA_ES,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": contenido_usuario}],
                }
            ],
        }

    # -- Lectura de la respuesta --------------------------------------------
    @staticmethod
    def _extraer_texto(crudo: bytes | str) -> str:
        """Extrae el texto generado del JSON de respuesta de Bedrock/Claude.

        Raises:
            LlmError: si la respuesta no tiene el formato esperado o viene vacía.
        """
        if isinstance(crudo, bytes):
            crudo = crudo.decode("utf-8")
        datos = json.loads(crudo)
        bloques = datos.get("content", [])
        texto = "".join(
            b.get("text", "") for b in bloques if b.get("type") == "text"
        ).strip()
        if not texto:
            raise LlmError(
                "El modelo de lenguaje devolvió una respuesta vacía o con un "
                "formato inesperado."
            )
        return texto


__all__ = ["BedrockLlmProvider"]
