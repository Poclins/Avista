"""Tests del ``StorageRepo`` (tarea 5.1 — Módulo D).

Cubren las dos implementaciones intercambiables del puerto:

- ``LocalStorageRepo`` (secundaria, modo mock/local): guardar y recuperar por
  referencia, saneo de nombre y rechazo de traspaso de directorio.
- ``S3StorageRepo`` (primaria, AWS): cifrado en reposo al subir y URLs
  prefirmadas con vigencia recortada a ≤300 s (Requirement 11.4), usando un
  cliente S3 falso para no tocar AWS real.

Trazabilidad: Requirements 1.2 (almacenar vía ``StorageRepo`` y asociar su
ubicación) y 11.4 (cifrado en reposo + URLs prefirmadas ≤300 s).
"""

from __future__ import annotations

import io
from typing import Any

import pytest

from app.repositories.storage import (
    MAX_URL_EXPIRY_SECONDS,
    LocalStorageRepo,
    S3StorageRepo,
    StorageRepo,
    StoredFile,
)


def _file(contenido: bytes, nombre: str, tipo: str | None = None) -> StoredFile:
    return StoredFile(io.BytesIO(contenido), nombre, tipo)


# ---------------------------------------------------------------------------
# Intercambiabilidad del contrato (LSP): ambas son StorageRepo
# ---------------------------------------------------------------------------
def test_adaptadores_son_storage_repo(tmp_path: Any) -> None:
    local = LocalStorageRepo(tmp_path)
    s3 = S3StorageRepo("bucket", client=_FakeS3())
    assert isinstance(local, StorageRepo)
    assert isinstance(s3, StorageRepo)


# ---------------------------------------------------------------------------
# LocalStorageRepo (secundaria)
# ---------------------------------------------------------------------------
def test_local_put_devuelve_ref_y_persiste(tmp_path: Any) -> None:
    repo = LocalStorageRepo(tmp_path)
    ref = repo.put(_file(b"audio-bytes", "nota.mp3", "audio/mpeg"))
    assert isinstance(ref, str) and ref
    # El archivo quedó escrito con el contenido original.
    destino = tmp_path / ref
    assert destino.exists()
    assert destino.read_bytes() == b"audio-bytes"


def test_local_get_url_recupera_el_mismo_medio(tmp_path: Any) -> None:
    repo = LocalStorageRepo(tmp_path)
    ref = repo.put(_file(b"foto-bytes", "evidencia.jpg"))
    url = repo.get_url(ref)
    assert url.startswith("file://")


def test_local_refs_distintas_para_mismo_nombre(tmp_path: Any) -> None:
    repo = LocalStorageRepo(tmp_path)
    ref1 = repo.put(_file(b"a", "nota.txt"))
    ref2 = repo.put(_file(b"b", "nota.txt"))
    assert ref1 != ref2  # el uuid evita colisiones


def test_local_sanea_nombre_peligroso(tmp_path: Any) -> None:
    repo = LocalStorageRepo(tmp_path)
    ref = repo.put(_file(b"x", "../../etc/pwn d.mp4"))
    # La ref no contiene separadores de ruta ni espacios.
    assert "/" not in ref and "\\" not in ref and " " not in ref
    assert (tmp_path / ref).exists()


def test_local_get_url_ref_inexistente(tmp_path: Any) -> None:
    repo = LocalStorageRepo(tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.get_url("no-existe.bin")


def test_local_get_url_rechaza_traspaso_de_directorio(tmp_path: Any) -> None:
    repo = LocalStorageRepo(tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.get_url("../secreto.txt")


# ---------------------------------------------------------------------------
# S3StorageRepo (primaria) — con cliente falso
# ---------------------------------------------------------------------------
class _FakeS3:
    """Doble mínimo del cliente S3 de boto3 para verificar el contrato."""

    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []
        self.presigned_calls: list[dict[str, Any]] = []

    def upload_fileobj(
        self, fileobj: Any, bucket: str, key: str, ExtraArgs: dict[str, Any] | None = None
    ) -> None:
        self.uploads.append(
            {
                "bucket": bucket,
                "key": key,
                "data": fileobj.read(),
                "extra": ExtraArgs or {},
            }
        )

    def generate_presigned_url(
        self, ClientMethod: str, Params: dict[str, Any], ExpiresIn: int
    ) -> str:
        self.presigned_calls.append(
            {"method": ClientMethod, "params": Params, "expires": ExpiresIn}
        )
        return (
            f"https://{Params['Bucket']}.s3.amazonaws.com/"
            f"{Params['Key']}?X-Amz-Expires={ExpiresIn}"
        )


def test_s3_put_cifra_en_reposo() -> None:
    fake = _FakeS3()
    repo = S3StorageRepo("jaimes-media", client=fake)
    ref = repo.put(_file(b"video-bytes", "clip.mp4", "video/mp4"))
    assert fake.uploads, "debió subir el objeto"
    subida = fake.uploads[0]
    assert subida["bucket"] == "jaimes-media"
    assert subida["key"] == ref
    assert subida["data"] == b"video-bytes"
    # Cifrado en reposo exigido por Requirement 11.4.
    assert subida["extra"].get("ServerSideEncryption") == "AES256"
    assert subida["extra"].get("ContentType") == "video/mp4"


def test_s3_get_url_es_prefirmada_sobre_la_ref() -> None:
    fake = _FakeS3()
    repo = S3StorageRepo("jaimes-media", client=fake)
    ref = repo.put(_file(b"x", "foto.jpg"))
    url = repo.get_url(ref)
    llamada = fake.presigned_calls[0]
    assert llamada["method"] == "get_object"
    assert llamada["params"] == {"Bucket": "jaimes-media", "Key": ref}
    assert url.startswith("https://")


def test_s3_get_url_vigencia_por_defecto_300s() -> None:
    fake = _FakeS3()
    repo = S3StorageRepo("jaimes-media", client=fake)
    repo.get_url("observaciones/abc_foto.jpg")
    assert fake.presigned_calls[0]["expires"] == MAX_URL_EXPIRY_SECONDS == 300


def test_s3_get_url_recorta_vigencia_a_300s() -> None:
    fake = _FakeS3()
    repo = S3StorageRepo("jaimes-media", client=fake)
    # Aun pidiendo más de 300 s, nunca se emite una URL de mayor vigencia.
    repo.get_url("observaciones/abc_foto.jpg", expires_in=86_400)
    assert fake.presigned_calls[0]["expires"] <= MAX_URL_EXPIRY_SECONDS


def test_s3_key_lleva_prefijo_y_es_unica() -> None:
    fake = _FakeS3()
    repo = S3StorageRepo("jaimes-media", client=fake, prefix="observaciones")
    ref1 = repo.put(_file(b"a", "nota.mp3"))
    ref2 = repo.put(_file(b"b", "nota.mp3"))
    assert ref1.startswith("observaciones/")
    assert ref1 != ref2
