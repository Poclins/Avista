"""Puerto de transcripción (Modelo 1): interfaz + adaptadores AWS/mock.

- ``TranscriptionProvider``: interfaz (puerto) del Módulo A.
- ``AwsTranscriptionProvider``: adaptador **primario** (Transcribe/Textract/
  Rekognition según formato).
- ``MockTranscriptionProvider``: adaptador **secundario** (local/CI) que deriva
  texto plausible del estilo del dataset E-1.

La selección entre AWS y mock la realiza el contenedor de DI según ``USE_MOCKS``.
"""

from app.providers.transcription.aws_transcription import AwsTranscriptionProvider
from app.providers.transcription.base import TranscriptionProvider
from app.providers.transcription.mock_transcription import MockTranscriptionProvider

__all__ = [
    "TranscriptionProvider",
    "AwsTranscriptionProvider",
    "MockTranscriptionProvider",
]
