"""Adaptador **AWS** del ``TranscriptionProvider`` (primario).

Enruta por ``formato`` a los servicios gestionados de AWS, detrás de la misma
interfaz que consume el ``TranscriptionService`` (Requirement 2.8):

- ``audio`` / ``video`` → **Amazon Transcribe** (voz a texto, es-CL)
  (Requirements 2.1, 2.3).
- ``foto`` → **Amazon Textract** (OCR de una nota manuscrita) (Requirement 2.2).
- ``video`` → además **Amazon Rekognition** para los **metadatos de escena**,
  que se anexan al texto transcrito (Requirement 2.4).

Robustez (Requirement 2.7): cada operación se **reintenta hasta 3 veces** ante
fallos transitorios; si el fallo persiste, se traduce a la excepción tipada
:class:`TranscriptionError` del Módulo A (en español) para que el
``TranscriptionService`` marque la observación como *pendiente de transcripción*
sin filtrar detalles del SDK.

Diseño verificable en aislamiento: los clientes boto3 (``transcribe``,
``textract``, ``rekognition``, ``s3``) se **inyectan** por el constructor; en los
tests se pasan dobles de prueba y nunca se llama a AWS real. Si no se inyectan,
se crean con la región de la configuración (camino de producción,
``USE_MOCKS=false``).
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

from app.domain.models import FormatoCaptura
from app.providers.errors import TranscriptionError
from app.providers.transcription.base import TranscriptionProvider

# Reintentos máximos por operación antes de marcar "pendiente de transcripción"
# (Requirement 2.7).
MAX_INTENTOS = 3

# Idioma de Amazon Transcribe para el español de Chile (Requirements 2.1, 2.3).
IDIOMA_TRANSCRIBE = "es-CL"

# Sondeo del trabajo asíncrono de Transcribe.
_INTERVALO_SONDEO_S = 2.0
_MAX_SONDEOS = 150  # ~300 s (Requirement 2.1), acotado por el plazo del formato.


class AwsTranscriptionProvider(TranscriptionProvider):
    """Implementación AWS (primaria) e intercambiable del puerto de transcripción.

    Implementa la interfaz ``TranscriptionProvider`` del Módulo A, de modo que es
    intercambiable con el mock bajo ``USE_MOCKS`` (LSP, Requirement 2.8). Los
    clientes boto3 solo se crean de forma perezosa en el camino real, por lo que
    importar o instanciar este adaptador no exige credenciales ni red.
    """

    def __init__(
        self,
        *,
        region: str = "us-east-1",
        transcribe_client: Any | None = None,
        textract_client: Any | None = None,
        rekognition_client: Any | None = None,
        s3_client: Any | None = None,
    ) -> None:
        self._region = region
        self._transcribe = transcribe_client
        self._textract = textract_client
        self._rekognition = rekognition_client
        self._s3 = s3_client

    # -- Fábricas perezosas de clientes (solo en el camino real) -------------
    def _client(self, servicio: str, inyectado: Any | None) -> Any:
        if inyectado is not None:
            return inyectado
        import boto3  # import diferido: solo necesario en producción.

        return boto3.client(servicio, region_name=self._region)

    # -- Enrutamiento por formato -------------------------------------------
    def transcribe(self, media_ref: str, formato: FormatoCaptura) -> str:
        """Transcribe o extrae texto de ``media_ref`` según ``formato``.

        Raises:
            TranscriptionError: si tras ``MAX_INTENTOS`` reintentos la operación
                sigue fallando o excede su plazo (Requirement 2.7), con mensaje
                en español.
        """
        if formato is FormatoCaptura.foto:
            return self._con_reintentos(
                lambda: self._textract_ocr(media_ref),
                "No se pudo extraer el texto de la foto",
            )

        if formato in (FormatoCaptura.audio, FormatoCaptura.video):
            texto = self._con_reintentos(
                lambda: self._transcribe_audio(media_ref),
                "No se pudo transcribir el audio del medio",
            )
            if formato is FormatoCaptura.video:
                # Los metadatos de escena son complementarios: si Rekognition
                # falla tras los reintentos no se pierde la transcripción.
                try:
                    escena = self._con_reintentos(
                        lambda: self._rekognition_escena(media_ref),
                        "No se pudieron obtener los metadatos de escena",
                    )
                except TranscriptionError:
                    escena = ""
                if escena:
                    texto = f"{texto} [Escena: {escena}.]"
            return texto

        # ``texto`` directo no se transcribe (lo maneja el servicio).
        return media_ref

    # -- Reintentos ----------------------------------------------------------
    def _con_reintentos(self, operacion: Any, mensaje_es: str) -> str:
        """Ejecuta ``operacion`` reintentando hasta ``MAX_INTENTOS`` veces."""
        ultimo_error: Exception | None = None
        for intento in range(1, MAX_INTENTOS + 1):
            try:
                return operacion()
            except TranscriptionError:
                raise
            except Exception as exc:  # fallos del SDK AWS u otros transitorios
                ultimo_error = exc
                if intento < MAX_INTENTOS:
                    time.sleep(min(2 ** (intento - 1), 4))
        raise TranscriptionError(
            f"{mensaje_es} tras {MAX_INTENTOS} intentos; "
            "la observación queda pendiente de transcripción."
        ) from ultimo_error

    # -- Operaciones por servicio -------------------------------------------
    @staticmethod
    def _s3_uri(media_ref: str) -> str:
        """Normaliza ``media_ref`` a una URI ``s3://bucket/clave``."""
        if media_ref.startswith("s3://"):
            return media_ref
        return f"s3://{media_ref}"

    def _transcribe_audio(self, media_ref: str) -> str:
        """Lanza y sondea un trabajo de Amazon Transcribe; devuelve el texto."""
        cliente = self._client("transcribe", self._transcribe)
        nombre_trabajo = f"jaimes-{abs(hash(media_ref)) & 0xFFFFFFFF:08x}"
        cliente.start_transcription_job(
            TranscriptionJobName=nombre_trabajo,
            LanguageCode=IDIOMA_TRANSCRIBE,
            Media={"MediaFileUri": self._s3_uri(media_ref)},
        )

        for _ in range(_MAX_SONDEOS):
            resp = cliente.get_transcription_job(TranscriptionJobName=nombre_trabajo)
            job = resp["TranscriptionJob"]
            estado = job["TranscriptionJobStatus"]
            if estado == "COMPLETED":
                uri = job["Transcript"]["TranscriptFileUri"]
                return self._leer_transcripcion(uri)
            if estado == "FAILED":
                raise TranscriptionError(
                    "Amazon Transcribe no pudo procesar el medio; "
                    "la observación queda pendiente de transcripción."
                )
            time.sleep(_INTERVALO_SONDEO_S)

        raise TranscriptionError(
            "La transcripción excedió el plazo máximo; "
            "la observación queda pendiente de transcripción."
        )

    @staticmethod
    def _leer_transcripcion(uri: str) -> str:
        """Descarga el JSON de resultado de Transcribe y extrae el texto."""
        with urllib.request.urlopen(uri) as f:  # noqa: S310 (URI firmada de AWS)
            datos = json.loads(f.read().decode("utf-8"))
        transcripts = datos.get("results", {}).get("transcripts", [])
        return " ".join(t.get("transcript", "") for t in transcripts).strip()

    def _textract_ocr(self, media_ref: str) -> str:
        """Extrae texto por OCR de una foto con Amazon Textract."""
        cliente = self._client("textract", self._textract)
        bucket, _, clave = self._s3_uri(media_ref)[len("s3://") :].partition("/")
        resp = cliente.detect_document_text(
            Document={"S3Object": {"Bucket": bucket, "Name": clave}}
        )
        lineas = [
            bloque["Text"]
            for bloque in resp.get("Blocks", [])
            if bloque.get("BlockType") == "LINE" and "Text" in bloque
        ]
        return "\n".join(lineas).strip()

    def _rekognition_escena(self, media_ref: str) -> str:
        """Obtiene etiquetas de escena de un video con Amazon Rekognition.

        Usa ``detect_labels`` sobre el objeto S3 y devuelve las etiquetas más
        relevantes como una cadena legible (metadatos de escena, Requirement 2.4).
        """
        cliente = self._client("rekognition", self._rekognition)
        bucket, _, clave = self._s3_uri(media_ref)[len("s3://") :].partition("/")
        resp = cliente.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": clave}},
            MaxLabels=5,
        )
        etiquetas = [
            e["Name"] for e in resp.get("Labels", []) if e.get("Name")
        ]
        return ", ".join(etiquetas)


__all__ = [
    "AwsTranscriptionProvider",
    "MAX_INTENTOS",
    "IDIOMA_TRANSCRIBE",
]
