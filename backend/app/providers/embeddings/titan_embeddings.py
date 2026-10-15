"""Adaptador AWS (primario) del :class:`EmbeddingProvider` con Amazon Titan.

Invoca **Amazon Titan Text Embeddings** vía Amazon Bedrock Runtime
(``invoke_model``) para convertir el texto de una observación en un vector denso
(Requirements 4.2, 4.5). Es el camino principal cuando ``USE_MOCKS=false`` y hay
credenciales AWS; comparte interfaz con el mock, por lo que son intercambiables
(LSP) sin tocar el código del servicio.

Contrato de error: cualquier fallo del SDK (credenciales, red, respuesta
inesperada) se traduce a :class:`EmbeddingError`, de modo que los servicios y la
capa de API dependan del contrato estable del Módulo A y no de los errores
crudos de boto3 (Requirement 4.4).
"""

from __future__ import annotations

import json
from typing import Any

from app.providers.embeddings.base import EmbeddingProvider
from app.providers.errors import EmbeddingError

# Dimensión por defecto de amazon.titan-embed-text-v2:0 (1024). Se mantiene
# alineada con el mock para que ambos adaptadores sean intercambiables.
DEFAULT_DIMENSION = 1024


class TitanEmbeddingProvider(EmbeddingProvider):
    """Proveedor de embeddings respaldado por Amazon Titan (Bedrock).

    Args:
        client: cliente ``bedrock-runtime`` de boto3 ya construido. Se inyecta
            (DIP) para que el contenedor de DI lo cree con región/credenciales y
            para poder sustituirlo por un doble en pruebas.
        model_id: identificador del modelo de embeddings de Titan.
        dimensions: dimensión de salida solicitada a Titan v2 (opcional). Si es
            ``None`` se usa la dimensión por defecto del modelo.
        normalize: si Titan debe normalizar el vector (v2); por defecto ``True``,
            recomendado para búsqueda por similitud coseno.
    """

    def __init__(
        self,
        client: Any,
        model_id: str = "amazon.titan-embed-text-v2:0",
        dimensions: int | None = DEFAULT_DIMENSION,
        normalize: bool = True,
    ) -> None:
        self._client = client
        self._model_id = model_id
        self._dimensions = dimensions
        self._normalize = normalize

    def embed(self, text: str) -> list[float]:
        """Genera el embedding del texto invocando Titan vía Bedrock.

        Raises:
            EmbeddingError: si el texto es vacío, si el SDK falla, o si la
                respuesta de Titan no contiene un vector válido.
        """
        if not text or not text.strip():
            raise EmbeddingError("El texto a embeber no puede estar vacío.")

        body = self._build_request_body(text)

        try:
            response = self._client.invoke_model(
                modelId=self._model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            payload = self._read_body(response)
            embedding = payload["embedding"]
        except EmbeddingError:
            raise
        except Exception as exc:  # boto3/ClientError, red, JSON, claves ausentes
            raise EmbeddingError(
                "No se pudo generar el embedding con Amazon Titan."
            ) from exc

        if not isinstance(embedding, list) or not embedding:
            raise EmbeddingError(
                "La respuesta de Amazon Titan no contiene un embedding válido."
            )
        return [float(component) for component in embedding]

    def _build_request_body(self, text: str) -> dict[str, Any]:
        """Arma el cuerpo de la petición de Titan Text Embeddings."""
        body: dict[str, Any] = {"inputText": text}
        if self._dimensions is not None:
            body["dimensions"] = self._dimensions
        body["normalize"] = self._normalize
        return body

    @staticmethod
    def _read_body(response: dict[str, Any]) -> dict[str, Any]:
        """Extrae y decodifica el JSON del campo ``body`` de la respuesta."""
        raw = response["body"]
        # El SDK devuelve un StreamingBody con ``.read()``; en pruebas puede ser
        # ya ``bytes`` o ``str``.
        if hasattr(raw, "read"):
            raw = raw.read()
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        return json.loads(raw)


__all__ = ["TitanEmbeddingProvider", "DEFAULT_DIMENSION"]
