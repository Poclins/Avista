"""Pruebas locales de normalización y transcript de Nova Sonic (sin red)."""

from __future__ import annotations

import asyncio
import json
import struct
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

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
