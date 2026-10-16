"""Pruebas locales de normalización y transcript de Nova Sonic (sin red)."""

from __future__ import annotations

import asyncio
import json
import struct
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.models import FormatoCaptura
from app.providers.errors import TranscriptionError
from app.providers.transcription.nova_sonic import NovaSonicTranscriptionProvider


def _provider(tmp_path: Path) -> NovaSonicTranscriptionProvider:
    return NovaSonicTranscriptionProvider(
        api_key="clave-de-prueba",
        storage_dir=tmp_path,
        max_seconds=5,
    )


def test_normaliza_wav_estereo_44k_a_pcm_mono_16k(tmp_path: Path) -> None:
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(44_100)
        frame = struct.pack("<hh", 1000, -1000)
        wav.writeframes(frame * 44_100)

    pcm = _provider(tmp_path)._leer_y_normalizar_wav(path)

    assert len(pcm) == 16_000 * 2


def test_rechaza_archivo_que_no_es_audio(tmp_path: Path) -> None:
    path = tmp_path / "audio.txt"
    path.write_bytes(b"no es audio")

    with pytest.raises(TranscriptionError, match="WAV"):
        _provider(tmp_path)._resolver_archivo(path.name)


class _OutputStream:
    def __init__(self, events: list[dict]) -> None:
        self._events = events

    def __aiter__(self):
        self._iterator = iter(self._events)
        return self

    async def __anext__(self):
        try:
            event = next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration
        value = SimpleNamespace(bytes_=json.dumps({"event": event}).encode())
        return SimpleNamespace(value=value)


class _Stream:
    def __init__(self, events: list[dict]) -> None:
        self._output = _OutputStream(events)

    async def await_output(self):
        return None, self._output


def test_extrae_solo_transcript_del_usuario(tmp_path: Path) -> None:
    events = [
        {"contentStart": {"contentName": "u", "role": "USER"}},
        {"textOutput": {"contentName": "u", "content": "El niño "}},
        {"textOutput": {"contentName": "u", "content": "compartió."}},
        {"contentEnd": {"contentName": "u"}},
        {"contentStart": {"contentName": "a", "role": "ASSISTANT"}},
        {"textOutput": {"contentName": "a", "content": "No incluir"}},
        {"sessionEnd": {}},
    ]
    done = asyncio.Event()

    transcript = asyncio.run(
        _provider(tmp_path)._recibir_transcript(_Stream(events), done)
    )

    assert transcript == "El niño compartió."
    assert done.is_set()


def test_sin_api_key_usa_sigv4_desde_el_primer_intento(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "audio.mp3"
    path.write_bytes(b"audio-de-prueba")
    provider = NovaSonicTranscriptionProvider(
        api_key=None,
        storage_dir=tmp_path,
        max_seconds=5,
    )
    modos: list[bool] = []

    monkeypatch.setattr(provider, "_leer_y_normalizar_audio", lambda _path: b"pcm")

    async def fake_transcribir(pcm: bytes, *, use_bearer: bool) -> str:
        assert pcm == b"pcm"
        modos.append(use_bearer)
        return "Transcripción SigV4"

    monkeypatch.setattr(provider, "_transcribir_pcm", fake_transcribir)

    assert provider.transcribe(path.name, FormatoCaptura.audio) == "Transcripción SigV4"
    assert modos == [False]


def test_credenciales_sigv4_provienen_de_boto3_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import boto3

    frozen = SimpleNamespace(
        access_key="access",
        secret_key="secret",
        token="session",
    )
    credentials = SimpleNamespace(get_frozen_credentials=lambda: frozen)
    regiones: list[str] = []

    def fake_session(*, region_name: str):
        regiones.append(region_name)
        return SimpleNamespace(get_credentials=lambda: credentials)

    monkeypatch.setattr(boto3, "Session", fake_session)
    provider = NovaSonicTranscriptionProvider(
        api_key="",
        region="us-east-1",
        storage_dir=tmp_path,
    )

    assert provider._credenciales_sesion() == ("access", "secret", "session")
    assert regiones == ["us-east-1"]
