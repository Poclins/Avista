"""Tests del ``TranscriptionService`` (Módulo D, tarea 5.3).

Verifican en aislamiento (con un ``TranscriptionProvider`` falso) la validación
de formato/tamaño y el enrutamiento por ``formato_captura`` (Requirements 1.4,
2.5, 2.6):

- Texto directo 1–50.000 caracteres se usa tal cual, **sin** llamar al proveedor.
- Límites de longitud del texto directo (vacío / excede 50.000).
- Límites de tamaño por formato (100 MB general, 10 MB foto, 500 MB video).
- Rechazo de formatos/extensiones no soportados, con mensaje en español.
- Enrutamiento de audio/foto/video al proveedor inyectado.
"""

from __future__ import annotations

import pytest

from app.domain.models import FormatoCaptura
from app.providers.errors import TranscriptionError
from app.providers.transcription.base import TranscriptionProvider
from app.services.transcription_service import (
    TAMANO_MAX_GENERAL,
    TEXTO_MAX_CHARS,
    MediaInput,
    TranscriptionService,
)

_MB = 1024 * 1024


# ===========================================================================
# Doble de prueba: proveedor que registra las llamadas y devuelve texto fijo
# ===========================================================================
class _FakeProvider(TranscriptionProvider):
    def __init__(self, texto: str = "texto transcrito") -> None:
        self._texto = texto
        self.llamadas: list[tuple[str, FormatoCaptura]] = []

    def transcribe(self, media_ref: str, formato: FormatoCaptura) -> str:
        self.llamadas.append((media_ref, formato))
        return self._texto


class _FailingProvider(TranscriptionProvider):
    def transcribe(self, media_ref: str, formato: FormatoCaptura) -> str:
        raise TranscriptionError("fallo del proveedor")


def _servicio(provider: TranscriptionProvider | None = None) -> TranscriptionService:
    return TranscriptionService(provider or _FakeProvider())


# ===========================================================================
# Texto directo (Requirement 2.5)
# ===========================================================================
def test_texto_directo_se_usa_tal_cual_sin_transcribir() -> None:
    fake = _FakeProvider()
    svc = TranscriptionService(fake)
    entrada = "La niña apiló tres cubos y nombró cada color."
    salida = svc.obtener_texto(MediaInput(formato=FormatoCaptura.texto, texto=entrada))
    assert salida == entrada
    assert fake.llamadas == [], "el texto directo no debe invocar al proveedor"


def test_texto_de_un_caracter_es_valido() -> None:
    svc = _servicio()
    assert svc.obtener_texto(MediaInput(formato=FormatoCaptura.texto, texto="x")) == "x"


def test_texto_en_el_limite_maximo_es_valido() -> None:
    svc = _servicio()
    entrada = "a" * TEXTO_MAX_CHARS
    assert svc.obtener_texto(
        MediaInput(formato=FormatoCaptura.texto, texto=entrada)
    ) == entrada


def test_texto_vacio_se_rechaza() -> None:
    svc = _servicio()
    with pytest.raises(TranscriptionError):
        svc.obtener_texto(MediaInput(formato=FormatoCaptura.texto, texto=""))


def test_texto_sin_contenido_se_rechaza() -> None:
    svc = _servicio()
    with pytest.raises(TranscriptionError):
        svc.obtener_texto(MediaInput(formato=FormatoCaptura.texto, texto=None))


def test_texto_que_excede_el_maximo_se_rechaza() -> None:
    svc = _servicio()
    entrada = "a" * (TEXTO_MAX_CHARS + 1)
    with pytest.raises(TranscriptionError) as exc:
        svc.obtener_texto(MediaInput(formato=FormatoCaptura.texto, texto=entrada))
    assert "excede" in str(exc.value)
    assert "caracteres" in str(exc.value)


# ===========================================================================
# Enrutamiento de medios no textuales (Requirements 2.1–2.4)
# ===========================================================================
@pytest.mark.parametrize(
    ("formato", "filename"),
    [
        (FormatoCaptura.audio, "obs.mp3"),
        (FormatoCaptura.audio, "obs.m4a"),
        (FormatoCaptura.audio, "obs.wav"),
        (FormatoCaptura.foto, "nota.jpg"),
        (FormatoCaptura.foto, "nota.jpeg"),
        (FormatoCaptura.foto, "nota.png"),
        (FormatoCaptura.video, "clip.mp4"),
        (FormatoCaptura.video, "clip.mov"),
    ],
)
def test_medio_valido_se_enruta_al_proveedor(
    formato: FormatoCaptura, filename: str
) -> None:
    fake = _FakeProvider("resultado")
    svc = TranscriptionService(fake)
    salida = svc.obtener_texto(
        MediaInput(
            formato=formato,
            media_ref="s3://jaimes-media/x",
            filename=filename,
            size_bytes=_MB,
        )
    )
    assert salida == "resultado"
    assert fake.llamadas == [("s3://jaimes-media/x", formato)]


def test_extension_mayusculas_es_aceptada() -> None:
    fake = _FakeProvider()
    svc = TranscriptionService(fake)
    svc.obtener_texto(
        MediaInput(
            formato=FormatoCaptura.foto,
            media_ref="ref",
            filename="NOTA.JPG",
            size_bytes=_MB,
        )
    )
    assert fake.llamadas, "la extensión en mayúsculas debe aceptarse"


def test_error_del_proveedor_se_propaga() -> None:
    svc = TranscriptionService(_FailingProvider())
    with pytest.raises(TranscriptionError):
        svc.obtener_texto(
            MediaInput(
                formato=FormatoCaptura.audio,
                media_ref="ref",
                filename="a.mp3",
                size_bytes=_MB,
            )
        )


def test_medio_sin_referencia_se_rechaza() -> None:
    svc = _servicio()
    with pytest.raises(TranscriptionError):
        svc.obtener_texto(
            MediaInput(
                formato=FormatoCaptura.audio,
                media_ref=None,
                filename="a.mp3",
                size_bytes=_MB,
            )
        )


# ===========================================================================
# Validación de formato (Requirement 1.4)
# ===========================================================================
@pytest.mark.parametrize(
    ("formato", "filename"),
    [
        (FormatoCaptura.audio, "obs.ogg"),
        (FormatoCaptura.foto, "nota.gif"),
        (FormatoCaptura.video, "clip.avi"),
        (FormatoCaptura.foto, "sin_extension"),
    ],
)
def test_formato_no_soportado_se_rechaza(
    formato: FormatoCaptura, filename: str
) -> None:
    fake = _FakeProvider()
    svc = TranscriptionService(fake)
    with pytest.raises(TranscriptionError) as exc:
        svc.obtener_texto(
            MediaInput(
                formato=formato,
                media_ref="ref",
                filename=filename,
                size_bytes=_MB,
            )
        )
    assert "no soportado" in str(exc.value)
    assert fake.llamadas == [], "no debe transcribirse un formato inválido"


# ===========================================================================
# Validación de tamaño por formato (Requirement 2.6)
# ===========================================================================
@pytest.mark.parametrize(
    ("formato", "filename", "limite"),
    [
        (FormatoCaptura.audio, "a.mp3", TAMANO_MAX_GENERAL),
        (FormatoCaptura.foto, "f.jpg", 10 * _MB),
        (FormatoCaptura.video, "v.mp4", 500 * _MB),
    ],
)
def test_tamano_en_el_limite_es_valido(
    formato: FormatoCaptura, filename: str, limite: int
) -> None:
    fake = _FakeProvider()
    svc = TranscriptionService(fake)
    svc.obtener_texto(
        MediaInput(
            formato=formato, media_ref="ref", filename=filename, size_bytes=limite
        )
    )
    assert fake.llamadas, "un tamaño en el límite debe aceptarse"


@pytest.mark.parametrize(
    ("formato", "filename", "limite"),
    [
        (FormatoCaptura.audio, "a.mp3", TAMANO_MAX_GENERAL),
        (FormatoCaptura.foto, "f.jpg", 10 * _MB),
        (FormatoCaptura.video, "v.mp4", 500 * _MB),
    ],
)
def test_tamano_que_excede_el_limite_se_rechaza(
    formato: FormatoCaptura, filename: str, limite: int
) -> None:
    fake = _FakeProvider()
    svc = TranscriptionService(fake)
    with pytest.raises(TranscriptionError) as exc:
        svc.obtener_texto(
            MediaInput(
                formato=formato,
                media_ref="ref",
                filename=filename,
                size_bytes=limite + 1,
            )
        )
    assert "excede el límite" in str(exc.value)
    assert fake.llamadas == []


def test_foto_mas_estricta_que_el_limite_general() -> None:
    """Una foto de 11 MB se rechaza aunque esté bajo el límite general de 100 MB."""
    fake = _FakeProvider()
    svc = TranscriptionService(fake)
    with pytest.raises(TranscriptionError):
        svc.obtener_texto(
            MediaInput(
                formato=FormatoCaptura.foto,
                media_ref="ref",
                filename="f.jpg",
                size_bytes=11 * _MB,
            )
        )


def test_tamano_cero_se_rechaza() -> None:
    svc = _servicio()
    with pytest.raises(TranscriptionError):
        svc.obtener_texto(
            MediaInput(
                formato=FormatoCaptura.audio,
                media_ref="ref",
                filename="a.mp3",
                size_bytes=0,
            )
        )


def test_tamano_desconocido_se_rechaza() -> None:
    svc = _servicio()
    with pytest.raises(TranscriptionError):
        svc.obtener_texto(
            MediaInput(
                formato=FormatoCaptura.audio,
                media_ref="ref",
                filename="a.mp3",
                size_bytes=None,
            )
        )
