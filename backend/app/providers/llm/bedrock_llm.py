"""Adaptador Amazon Bedrock para Claude mediante la API Converse."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider

_MAX_TOKENS = 4096
_SISTEMA_ES = (
    "Eres un asistente pedagógico que redacta en español de Chile. "
    "Responde siempre en español, de forma clara y profesional, "
    "fundamentando cada afirmación únicamente en el contexto entregado."
)


class BedrockLlmProvider(LlmProvider):
    """Genera texto con Converse usando IAM o una API key Bearer local."""

    def __init__(
        self,
        *,
        region: str | None = None,
        model_id: str | None = None,
        timeout_segundos: float | None = None,
        max_tokens: int = _MAX_TOKENS,
        temperatura: float = 0.2,
        bedrock_runtime_client: Any | None = None,
        api_key: str | None = None,
        urlopen_func: Any | None = None,
    ) -> None:
        settings = get_settings()
        self._region = region or settings.aws_region
        self._model_id = model_id or settings.bedrock_model_id
        self._timeout = (
            timeout_segundos
            if timeout_segundos is not None
            else float(getattr(settings, "llm_timeout_segundos", 60.0))
        )
        self._max_tokens = max_tokens
        # Se conserva el parámetro por compatibilidad, pero Converse para
        # Claude Sonnet 5 no envía temperature.
        self._temperatura = temperatura
        self._client = bedrock_runtime_client
        self._api_key = (api_key or "").strip() or None
        self._urlopen = urlopen_func or urlopen

    def _runtime(self) -> Any:
        if self._client is not None:
            return self._client
        import boto3
        from botocore.config import Config

        config = Config(
            region_name=self._region,
            read_timeout=self._timeout,
            connect_timeout=min(self._timeout, 10.0),
            retries={"max_attempts": 0},
        )
        self._client = boto3.client("bedrock-runtime", config=config)
        return self._client

    def generate(self, prompt: str, context: str) -> str:
        """Genera texto en español y traduce fallos del proveedor."""
        if self._api_key:
            return self._generar_con_api_key(prompt, context)

        cuerpo = self._construir_converse(prompt, context)
        try:
            respuesta = self._runtime().converse(
                modelId=self._model_id,
                **cuerpo,
            )
            return self._extraer_texto_converse(respuesta)
        except LlmError:
            raise
        except Exception as exc:
            raise LlmError(
                "No se pudo generar el texto con el modelo de lenguaje "
                "(fallo o tiempo de espera agotado del proveedor)."
            ) from exc

    def _generar_con_api_key(self, prompt: str, context: str) -> str:
        """Invoca Converse por HTTPS usando una API key Bearer de Bedrock."""
        model_id = quote(self._model_id, safe=".:_-")
        endpoint = (
            f"https://bedrock-runtime.{self._region}.amazonaws.com/"
            f"model/{model_id}/converse"
        )
        cuerpo = self._construir_converse(prompt, context)
        solicitud = Request(
            endpoint,
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with self._urlopen(solicitud, timeout=self._timeout) as respuesta:
                return self._extraer_texto_converse(respuesta.read())
        except LlmError:
            raise
        except Exception as exc:
            raise LlmError(
                "No se pudo generar el texto con Amazon Bedrock. Verifique "
                "la API key, el acceso al modelo y la región configurada."
            ) from exc

    def _construir_converse(self, prompt: str, context: str) -> dict[str, Any]:
        """Construye Converse sin temperature y con thinking deshabilitado."""
        contenido = (
            f"Contexto fundamentante:\n{context}\n\n"
            f"Instrucción:\n{prompt}"
        )
        return {
            "system": [{"text": _SISTEMA_ES}],
            "messages": [
                {"role": "user", "content": [{"text": contenido}]}
            ],
            "inferenceConfig": {"maxTokens": self._max_tokens},
            "additionalModelRequestFields": {
                "thinking": {"type": "disabled"}
            },
        }

    @staticmethod
    def _extraer_texto_converse(
        crudo: bytes | str | dict[str, Any],
    ) -> str:
        """Extrae texto tanto de boto3 Converse como de la respuesta HTTP."""
        if isinstance(crudo, bytes):
            crudo = crudo.decode("utf-8")
        datos = json.loads(crudo) if isinstance(crudo, str) else crudo
        bloques = datos.get("output", {}).get("message", {}).get("content", [])
        texto = "".join(
            bloque.get("text", "")
            for bloque in bloques
            if isinstance(bloque, dict)
        ).strip()
        if not texto:
            raise LlmError(
                "El modelo de lenguaje devolvió una respuesta vacía o inválida."
            )
        return texto


__all__ = ["BedrockLlmProvider"]
