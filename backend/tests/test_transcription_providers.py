"""Tests del ``TranscriptionProvider`` — adaptadores AWS (primario) y mock.

Verifican el contrato del Módulo D (tarea 5.2) en aislamiento, sin llamar a AWS
real: el adaptador AWS recibe **clientes boto3 falsos** por inyección. Cubren:

- Intercambiabilidad: ambos adaptadores son ``TranscriptionProvider`` (LSP,
  Requirement 2.8).
- Enrutamiento por formato (Requirements 2.1–2.4): audio/video → Transcribe,
  foto → Textract, video → además Rekognition (metadatos de escena).
- Reintentos ≤3 y, si el fallo persiste, ``TranscriptionError`` en español que
  deja la observación "pendiente de transcripción" (Requirement 2.7).
- Determinismo del mock (misma referencia ⇒ mismo texto).
"""

from __future__ import annotations

import pytest

from app.domain.models import FormatoCaptura
from app.providers.errors import TranscriptionError
from app.providers.transcription.aws_transcription import (
    MAX_INTENTOS,
    AwsTranscriptionProvider,
)
from app.providers.transcription.base import TranscriptionProvider
from app.providers.transcription.mock_transcription import (
    FAIL_MARKER,
    MockTranscriptionProvider,
)


# ===========================================================================
# Dobles de prueba de los clientes boto3 (sin red ni credenciales)
# ===========================================================================
class _FakeTranscribe:
    """Transcribe falso: completa inmediatamente devolviendo un texto fijo."""

    def __init__(self, texto: str = "texto transcrito de prueba") -> None:
        self._texto = texto
        self.jobs: list[str] = []

    def start_transcription_job(self, **kwargs: object) -> dict:
        self.jobs.append(str(kwargs.get("TranscriptionJobName")))
        return {}

    def get_transcription_job(self, **kwargs: object) -> dict:
        return {
            "TranscriptionJob": {
                "TranscriptionJobStatus": "COMPLETED",
                "Transcript": {"TranscriptFileUri": f"memory://{self._texto}"},
            }
        }


class _FakeTranscribeFailing:
    """Transcribe falso que siempre reporta el trabajo como FAILED."""

    def __init__(self) -> None:
        self.start_calls = 0

    def start_transcription_job(self, **kwargs: object) -> dict:
        self.start_calls += 1
        return {}

    def get_transcription_job(self, **kwargs: object) -> dict:
        return {"TranscriptionJob": {"TranscriptionJobStatus": "FAILED"}}


class _FakeTextract:
    def __init__(self, lineas: list[str] | None = None) -> None:
        self.lineas = lineas or ["Nota de la tia:", "abrocho su delantal solo"]
        self.calls = 0

    def detect_document_text(self, **kwargs: object) -> dict:
        self.calls += 1
        bloques = [{"BlockType": "PAGE"}]
        bloques += [{"BlockType": "LINE", "Text": t} for t in self.lineas]
        return {"Blocks": bloques}


class _RaisingClient:
    """Cliente que lanza en cada llamada, para probar los reintentos."""

    def __init__(self) -> None:
        self.calls = 0

    def _boom(self, **kwargs: object) -> dict:
        self.calls += 1
        raise RuntimeError("fallo transitorio del SDK")

    detect_document_text = _boom
    start_transcription_job = _boom
    detect_labels = _boom


class _FakeRekognition:
    def __init__(self, etiquetas: list[str] | None = None) -> None:
        self.etiquetas = etiquetas or ["Classroom", "Toy", "Child"]
        self.calls = 0

    def detect_labels(self, **kwargs: object) -> dict:
        self.calls += 1
        return {"Labels": [{"Name": n} for n in self.etiquetas]}


def _patch_lectura(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita la descarga HTTP real del resultado de Transcribe.

    La URI falsa tiene la forma ``memory://<texto>``; devolvemos ese texto.
    """

    def _fake_leer(uri: str) -> str:
        return uri.replace("memory://", "")

    monkeypatch.setattr(
        AwsTranscriptionProvider, "_leer_transcripcion", staticmethod(_fake_leer)
    )


# ===========================================================================
# Intercambiabilidad (LSP)
# ===========================================================================
def test_ambos_adaptadores_son_el_puerto() -> None:
    assert issubclass(MockTranscriptionProvider, TranscriptionProvider)
    assert issubclass(AwsTranscriptionProvider, TranscriptionProvider)
    assert isinstance(MockTranscriptionProvider(), TranscriptionProvider)
    assert isinstance(
        AwsTranscriptionProvider(region="us-east-1"), TranscriptionProvider
    )


# ===========================================================================
# Adaptador mock
# ===========================================================================
@pytest.mark.parametrize(
    "formato",
    [FormatoCaptura.audio, FormatoCaptura.video, FormatoCaptura.foto],
)
def test_mock_devuelve_texto_no_vacio_por_formato(formato: FormatoCaptura) -> None:
    prov = MockTranscriptionProvider()
    texto = prov.transcribe("s3://jaimes-media/obs-001", formato)
    assert isinstance(texto, str)
    assert texto.strip() != ""


def test_mock_video_incluye_metadatos_de_escena() -> None:
    prov = MockTranscriptionProvider()
    texto = prov.transcribe("s3://jaimes-media/vid-1", FormatoCaptura.video)
    assert "[Escena:" in texto


def test_mock_foto_no_incluye_escena() -> None:
    prov = MockTranscriptionProvider()
    texto = prov.transcribe("s3://jaimes-media/foto-1", FormatoCaptura.foto)
    assert "[Escena:" not in texto


def test_mock_es_determinista() -> None:
    prov = MockTranscriptionProvider()
    ref = "s3://jaimes-media/obs-xyz"
    assert prov.transcribe(ref, FormatoCaptura.audio) == prov.transcribe(
        ref, FormatoCaptura.audio
    )


def test_mock_texto_directo_devuelve_la_referencia() -> None:
    prov = MockTranscriptionProvider()
    assert prov.transcribe("hola mundo", FormatoCaptura.texto) == "hola mundo"


def test_mock_fallo_simulado_lanza_transcription_error() -> None:
    prov = MockTranscriptionProvider()
    with pytest.raises(TranscriptionError):
        prov.transcribe(f"s3://b/{FAIL_MARKER}", FormatoCaptura.audio)


# ===========================================================================
# Adaptador AWS — enrutamiento por formato
# ===========================================================================
def test_aws_audio_usa_transcribe(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lectura(monkeypatch)
    fake = _FakeTranscribe("la niña apiló tres cubos")
    prov = AwsTranscriptionProvider(transcribe_client=fake)
    texto = prov.transcribe("jaimes-media/audio.mp3", FormatoCaptura.audio)
    assert texto == "la niña apiló tres cubos"
    assert fake.jobs, "se debió lanzar un trabajo de Transcribe"


def test_aws_foto_usa_textract() -> None:
    fake = _FakeTextract(["linea uno", "linea dos"])
    prov = AwsTranscriptionProvider(textract_client=fake)
    texto = prov.transcribe("jaimes-media/foto.jpg", FormatoCaptura.foto)
    assert texto == "linea uno\nlinea dos"
    assert fake.calls == 1


def test_aws_video_usa_transcribe_y_rekognition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lectura(monkeypatch)
    t = _FakeTranscribe("el niño siguió una instrucción")
    r = _FakeRekognition(["Classroom", "Toy"])
    prov = AwsTranscriptionProvider(transcribe_client=t, rekognition_client=r)
    texto = prov.transcribe("jaimes-media/video.mp4", FormatoCaptura.video)
    assert "el niño siguió una instrucción" in texto
    assert "[Escena: Classroom, Toy.]" in texto
    assert r.calls == 1


def test_aws_video_sin_escena_conserva_transcripcion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si Rekognition falla, no se pierde la transcripción (metadato opcional)."""
    _patch_lectura(monkeypatch)
    t = _FakeTranscribe("texto del video")
    prov = AwsTranscriptionProvider(
        transcribe_client=t, rekognition_client=_RaisingClient()
    )
    texto = prov.transcribe("jaimes-media/video.mp4", FormatoCaptura.video)
    assert texto == "texto del video"


def test_aws_texto_directo_no_transcribe() -> None:
    prov = AwsTranscriptionProvider()
    assert prov.transcribe("contenido directo", FormatoCaptura.texto) == (
        "contenido directo"
    )


# ===========================================================================
# Adaptador AWS — reintentos y marca de pendiente de transcripción
# ===========================================================================
def test_aws_reintenta_hasta_el_maximo_y_lanza_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.providers.transcription.aws_transcription.time.sleep",
        lambda *_: None,
    )
    cliente = _RaisingClient()
    prov = AwsTranscriptionProvider(textract_client=cliente)
    with pytest.raises(TranscriptionError) as exc:
        prov.transcribe("jaimes-media/foto.jpg", FormatoCaptura.foto)
    assert cliente.calls == MAX_INTENTOS
    assert "pendiente de transcripción" in str(exc.value)


def test_aws_transcribe_job_fallido_lanza_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.providers.transcription.aws_transcription.time.sleep",
        lambda *_: None,
    )
    prov = AwsTranscriptionProvider(transcribe_client=_FakeTranscribeFailing())
    with pytest.raises(TranscriptionError) as exc:
        prov.transcribe("jaimes-media/audio.mp3", FormatoCaptura.audio)
    assert "pendiente de transcripción" in str(exc.value)
