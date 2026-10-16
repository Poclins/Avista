"""Transcripción de audio local mediante Amazon Nova 2 Sonic.

Nova Sonic usa InvokeModelWithBidirectionalStream (HTTP/2). El proveedor recibe
un WAV PCM local, lo normaliza a PCM firmado de 16 bits, mono, 16 kHz, envía el
audio al modelo y devuelve únicamente el transcript del rol USER. Después, el
pipeline existente clasifica ese texto con Claude y lo persiste como observación.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.domain.models import FormatoCaptura
from app.providers.errors import TranscriptionError
from app.providers.transcription.base import TranscriptionProvider

_MODEL_ID = "amazon.nova-2-sonic-v1:0"
_INPUT_RATE = 16_000
_MAX_SECONDS = 60
_CHUNK_BYTES = 2_048  # 64 ms de PCM mono 16-bit a 16 kHz.
_BEARER_SCHEME_ID = "smithy.api#httpBearerAuth"


class _BearerResolver:
    """Fuerza el esquema Bearer que admite Bedrock Runtime."""

    def resolve_auth_scheme(self, auth_parameters: Any) -> list[Any]:
        from smithy_core.auth import AuthOption
        from smithy_core.shapes import ShapeID

        return [
            AuthOption(
                scheme_id=ShapeID(_BEARER_SCHEME_ID),
                identity_properties={},
                signer_properties={},
            )
        ]


class _BearerScheme:
    """Esquema Smithy mínimo que añade Authorization: Bearer <api-key>."""

    def __init__(self, api_key: str) -> None:
        from smithy_core.shapes import ShapeID
        from smithy_core.traits import APIKeyLocation
        from smithy_http.aio.auth.apikey import APIKeySigner

        self.scheme_id = ShapeID(_BEARER_SCHEME_ID)
        self._api_key = api_key
        self._signer = APIKeySigner(
            name="Authorization",
            location=APIKeyLocation.HEADER,
            scheme="Bearer",
        )

    def identity_properties(self, *, context: Any) -> dict[str, str]:
        return {"api_key": self._api_key}

    def identity_resolver(self, *, context: Any) -> Any:
        from smithy_http.aio.identity.apikey import APIKeyIdentityResolver

        return APIKeyIdentityResolver()

    def signer_properties(self, *, context: Any) -> dict[str, Any]:
        return {}

    def signer(self) -> Any:
        return self._signer

    def event_signer(self, *, request: Any) -> None:
        # Los eventos viajan dentro de la conexión HTTP/2 ya autenticada.
        return None


class NovaSonicTranscriptionProvider(TranscriptionProvider):
    """Transcribe archivos WAV mediante Nova 2 Sonic."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        region: str = "us-east-1",
        model_id: str = _MODEL_ID,
        storage_dir: str | Path = "./storage",
        max_seconds: int = _MAX_SECONDS,
        client_factory: Any | None = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._region = region
        self._model_id = model_id
        self._storage_dir = Path(storage_dir)
        self._max_seconds = max(1, int(max_seconds))
        self._client_factory = client_factory

    def transcribe(self, media_ref: str, formato: FormatoCaptura) -> str:
        if formato is not FormatoCaptura.audio:
            raise TranscriptionError("Nova Sonic solo admite audio en este flujo.")

        path = self._resolver_archivo(media_ref)
        pcm = self._leer_y_normalizar_audio(path)
        use_bearer = bool(self._api_key)

        async def ejecutar() -> str:
            return await asyncio.wait_for(
                self._transcribir_pcm(pcm, use_bearer=use_bearer),
                timeout=self._max_seconds + 35,
            )

        def correr() -> str:
            return asyncio.run(ejecutar())

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                return correr()
            except asyncio.TimeoutError as exc:
                raise TranscriptionError(
                    "La transcripción con Nova Sonic excedió el tiempo permitido."
                ) from exc

        # Compatibilidad si un llamador síncrono se ejecuta dentro de un loop.
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(correr)
        try:
            return future.result(timeout=self._max_seconds + 45)
        except FutureTimeout as exc:
            future.cancel()
            raise TranscriptionError(
                "La transcripción con Nova Sonic excedió el tiempo permitido."
            ) from exc
        except TranscriptionError:
            raise
        except Exception as exc:
            raise TranscriptionError(
                "Nova Sonic no pudo transcribir el audio. Verifique las "
                "credenciales, el acceso al modelo y que el archivo sea válido."
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _resolver_archivo(self, media_ref: str) -> Path:
        base = self._storage_dir.resolve()
        path = (base / media_ref).resolve()
        if base != path and base not in path.parents:
            raise TranscriptionError("La referencia del audio no es válida.")
        if not path.is_file():
            raise TranscriptionError("No se encontró el audio almacenado.")
        if path.suffix.lower() not in {".wav", ".ogg", ".opus", ".mp3"}:
            raise TranscriptionError(
                "Nova Sonic requiere audio WAV, OGG, Opus o MP3 para esta demo."
            )
        return path

    def _leer_y_normalizar_audio(self, path: Path) -> bytes:
        """Decodifica WAV/OGG/Opus y devuelve PCM mono 16-bit a 16 kHz."""
        try:
            import numpy as np
            import soundfile as sf

            muestras, frecuencia = sf.read(
                path,
                dtype="float32",
                always_2d=True,
            )
        except Exception as exc:
            raise TranscriptionError(
                "No se pudo decodificar el audio; use WAV, OGG, Opus o MP3 válido."
            ) from exc

        if frecuencia <= 0 or muestras.size == 0:
            raise TranscriptionError("El archivo no contiene audio válido.")
        duracion = len(muestras) / frecuencia
        if duracion <= 0 or duracion > self._max_seconds:
            raise TranscriptionError(
                f"El audio debe durar entre 1 y {self._max_seconds} segundos."
            )

        mono = muestras.mean(axis=1)
        if frecuencia != _INPUT_RATE:
            cantidad = max(1, int(len(mono) * _INPUT_RATE / frecuencia))
            posiciones = np.linspace(0, len(mono) - 1, cantidad)
            mono = np.interp(posiciones, np.arange(len(mono)), mono)

        pcm = np.clip(mono, -1.0, 1.0)
        pcm = (pcm * 32767).astype("<i2")
        return pcm.tobytes()

    # Alias conservado para pruebas/callers anteriores.
    def _leer_y_normalizar_wav(self, path: Path) -> bytes:
        return self._leer_y_normalizar_audio(path)

    def _credenciales_sesion(self) -> tuple[str, str, str | None]:
        """Obtiene credenciales temporales del rol mediante boto3.Session."""
        import boto3

        credentials = boto3.Session(region_name=self._region).get_credentials()
        if credentials is None:
            raise TranscriptionError(
                "No se encontraron credenciales AWS para Amazon Nova Sonic."
            )
        frozen = credentials.get_frozen_credentials()
        return frozen.access_key, frozen.secret_key, frozen.token

    def _crear_cliente(self, *, use_bearer: bool) -> Any:
        if self._client_factory is not None:
            return self._client_factory()

        from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient
        from aws_sdk_bedrock_runtime.config import Config
        from smithy_core.shapes import ShapeID
        from smithy_http.aio.crt import AWSCRTHTTPClient

        common = {
            "endpoint_uri": f"https://bedrock-runtime.{self._region}.amazonaws.com",
            "region": self._region,
            "transport": AWSCRTHTTPClient(),
        }
        if use_bearer:
            scheme = _BearerScheme(self._api_key)
            config = Config(
                **common,
                auth_scheme_resolver=_BearerResolver(),
                auth_schemes={ShapeID(_BEARER_SCHEME_ID): scheme},
            )
        else:
            from aws_sdk_bedrock_runtime.auth import HTTPAuthSchemeResolver
            from smithy_aws_core.auth import SigV4AuthScheme
            from smithy_aws_core.identity import (
                AWSCredentialsIdentity,
                StaticCredentialsResolver,
            )

            access_key, secret_key, session_token = self._credenciales_sesion()
            identity = AWSCredentialsIdentity(
                access_key_id=access_key,
                secret_access_key=secret_key,
                session_token=session_token,
            )
            config = Config(
                **common,
                auth_scheme_resolver=HTTPAuthSchemeResolver(),
                auth_schemes={
                    ShapeID("aws.auth#sigv4"): SigV4AuthScheme(service="bedrock")
                },
                aws_credentials_identity_resolver=StaticCredentialsResolver(identity),
            )
        return AsyncBedrockRuntimeClient(config=config)

    async def _enviar_evento(self, stream: Any, payload: dict[str, Any]) -> None:
        from aws_sdk_bedrock_runtime.models import (
            BidirectionalInputPayloadPart,
            InvokeModelWithBidirectionalStreamInputChunk,
        )

        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(
                bytes_=json.dumps(payload).encode("utf-8")
            )
        )
        await stream.input_stream.send(chunk)

    async def _transcribir_pcm(self, pcm: bytes, *, use_bearer: bool) -> str:
        from aws_sdk_bedrock_runtime.models import (
            InvokeModelWithBidirectionalStreamOperationInput,
        )

        client = self._crear_cliente(use_bearer=use_bearer)
        stream = await client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(
                model_id=self._model_id
            )
        )
        transcript_done = asyncio.Event()
        transcript_parts: list[str] = []
        transcript_task = asyncio.create_task(
            self._recibir_transcript(stream, transcript_done, transcript_parts)
        )

        prompt_name = str(uuid4())
        system_name = str(uuid4())
        audio_name = str(uuid4())

        try:
            await self._enviar_evento(
                stream,
                {
                    "event": {
                        "sessionStart": {
                            "inferenceConfiguration": {"maxTokens": 256},
                            "turnDetectionConfiguration": {
                                "endpointingSensitivity": "HIGH"
                            },
                        }
                    }
                },
            )
            await self._enviar_evento(
                stream,
                {
                    "event": {
                        "promptStart": {
                            "promptName": prompt_name,
                            "textOutputConfiguration": {"mediaType": "text/plain"},
                            "audioOutputConfiguration": {
                                "mediaType": "audio/lpcm",
                                "sampleRateHertz": 24000,
                                "sampleSizeBits": 16,
                                "channelCount": 1,
                                "voiceId": "matthew",
                                "encoding": "base64",
                                "audioType": "SPEECH",
                            },
                        }
                    }
                },
            )
            await self._enviar_evento(
                stream,
                {
                    "event": {
                        "contentStart": {
                            "promptName": prompt_name,
                            "contentName": system_name,
                            "type": "TEXT",
                            "interactive": True,
                            "role": "SYSTEM",
                            "textInputConfiguration": {"mediaType": "text/plain"},
                        }
                    }
                },
            )
            await self._enviar_evento(
                stream,
                {
                    "event": {
                        "textInput": {
                            "promptName": prompt_name,
                            "contentName": system_name,
                            "content": (
                                "Transcribe literalmente el audio del usuario en "
                                "español. No respondas, no resumas y no interpretes."
                            ),
                        }
                    }
                },
            )
            await self._enviar_evento(
                stream,
                {
                    "event": {
                        "contentEnd": {
                            "promptName": prompt_name,
                            "contentName": system_name,
                        }
                    }
                },
            )
            await self._enviar_evento(
                stream,
                {
                    "event": {
                        "contentStart": {
                            "promptName": prompt_name,
                            "contentName": audio_name,
                            "type": "AUDIO",
                            "interactive": True,
                            "role": "USER",
                            "audioInputConfiguration": {
                                "mediaType": "audio/lpcm",
                                "sampleRateHertz": _INPUT_RATE,
                                "sampleSizeBits": 16,
                                "channelCount": 1,
                                "audioType": "SPEECH",
                                "encoding": "base64",
                            },
                        }
                    }
                },
            )
            for offset in range(0, len(pcm), _CHUNK_BYTES):
                chunk = pcm[offset : offset + _CHUNK_BYTES]
                encoded = base64.b64encode(chunk).decode("ascii")
                await self._enviar_evento(
                    stream,
                    {
                        "event": {
                            "audioInput": {
                                "promptName": prompt_name,
                                "contentName": audio_name,
                                "content": encoded,
                            }
                        }
                    },
                )
                # Sonic procesa audio en tiempo real; no inundar el stream.
                await asyncio.sleep(len(chunk) / (_INPUT_RATE * 2))
            await self._enviar_evento(
                stream,
                {
                    "event": {
                        "contentEnd": {
                            "promptName": prompt_name,
                            "contentName": audio_name,
                        }
                    }
                },
            )
            # Esperar el cierre del contenido USER para asegurar que llegó el
            # transcript final antes de cerrar prompt/sesión.
            try:
                await asyncio.wait_for(transcript_done.wait(), timeout=15)
                # Sonic puede emitir varios segmentos USER consecutivos.
                await asyncio.sleep(3)
            except TimeoutError:
                pass
            await self._enviar_evento(
                stream, {"event": {"promptEnd": {"promptName": prompt_name}}}
            )
            await self._enviar_evento(stream, {"event": {"sessionEnd": {}}})
            await stream.input_stream.close()
            try:
                await asyncio.wait_for(transcript_task, timeout=3)
            except asyncio.TimeoutError:
                transcript_task.cancel()
            transcript = " ".join(transcript_parts)
        finally:
            if not transcript_task.done():
                transcript_task.cancel()
            try:
                await asyncio.wait_for(stream.close(), timeout=3)
            except (Exception, asyncio.TimeoutError):
                pass

        transcript = " ".join(transcript.split()).strip()
        transcript = re.sub(
            r"\.\s+(y|e|o|pero)\b", r" \1", transcript, flags=re.IGNORECASE
        )
        if transcript:
            transcript = transcript[0].upper() + transcript[1:]
        if not transcript:
            raise TranscriptionError(
                "Nova Sonic no detectó voz en el archivo de audio."
            )
        return transcript

    async def _recibir_transcript(
        self,
        stream: Any,
        transcript_done: asyncio.Event,
        partes: list[str] | None = None,
    ) -> str:
        _, output_stream = await stream.await_output()
        if partes is None:
            partes = []
        roles: dict[str, str] = {}
        rol_actual: str | None = None
        async for result in output_stream:
            value = getattr(result, "value", None)
            payload = getattr(value, "bytes_", None)
            if not payload:
                continue
            event = json.loads(payload.decode("utf-8")).get("event", {})
            if "contentStart" in event:
                inicio = event["contentStart"]
                rol_actual = inicio.get("role")
                nombre = inicio.get("contentName")
                if nombre and rol_actual:
                    roles[nombre] = rol_actual
            elif "textOutput" in event:
                salida = event["textOutput"]
                rol = roles.get(salida.get("contentName"), rol_actual)
                if rol == "USER":
                    partes.append(salida.get("content", ""))
            elif "contentEnd" in event:
                fin = event["contentEnd"]
                rol = roles.get(fin.get("contentName"), rol_actual)
                if rol == "USER":
                    transcript_done.set()
            elif "sessionEnd" in event:
                break
        return "".join(partes)


__all__ = ["NovaSonicTranscriptionProvider"]
