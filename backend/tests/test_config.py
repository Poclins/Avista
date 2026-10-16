"""Tests del armado de la URL de BD desde Secrets Manager (tarea 11.3, fix 1).

Verifican la lógica de :meth:`Settings.resolve_database_url` y el helper
:func:`construir_url_postgres`:

- **Modo mock / sin datos de Aurora:** se conserva la ``database_url`` por
  defecto (SQLite); no se toca boto3 ni red.
- **Camino AWS (``use_mocks=false`` + ``db_secret_arn`` + ``db_endpoint``):** se
  arma ``postgresql+psycopg://USER:PASS@ENDPOINT:PORT/NAME`` leyendo el secreto
  JSON (``username``/``password``) de Secrets Manager, **mockeando boto3** (sin
  llamadas reales a AWS).
- Las credenciales con caracteres especiales se **codifican** para no romper la
  URL.

Ningún test de este módulo contacta AWS: ``boto3.client`` se parchea.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.core.config import Settings, construir_url_postgres


# ---------------------------------------------------------------------------
# construir_url_postgres: codificación segura de credenciales
# ---------------------------------------------------------------------------
def test_construir_url_postgres_formato_basico() -> None:
    url = construir_url_postgres(
        usuario="jaimes_admin",
        clave="secreta123",
        host="host.rds.amazonaws.com",
        puerto=5432,
        base="jaimes",
    )
    assert url == (
        "postgresql+psycopg://jaimes_admin:secreta123@"
        "host.rds.amazonaws.com:5432/jaimes"
    )


def test_construir_url_postgres_codifica_caracteres_especiales() -> None:
    """Caracteres especiales en usuario/clave se codifican (sin romper la URL)."""
    url = construir_url_postgres(
        usuario="user@admin",
        clave="p@ss:w/rd?",
        host="h",
        puerto=5432,
        base="jaimes",
    )
    # '@', ':', '/', '?' quedan percent-encoded; el '@' separador real es el
    # último antes del host.
    assert "user%40admin" in url
    assert "p%40ss%3Aw%2Frd%3F" in url
    assert url.endswith("@h:5432/jaimes")
    # Un único '@' separador de credenciales↔host (los de las credenciales van
    # codificados), de modo que la URL sea inequívoca.
    assert url.count("@") == 1


# ---------------------------------------------------------------------------
# resolve_database_url: modo mock / sin datos de Aurora → SQLite por defecto
# ---------------------------------------------------------------------------
def test_resolve_url_modo_mock_devuelve_sqlite_por_defecto() -> None:
    settings = Settings(environment="development", database_url="sqlite:///./jaimes.db")
    assert settings.resolve_database_url() == "sqlite:///./jaimes.db"


def test_resolve_url_sin_secreto_no_arma_postgres() -> None:
    """Con ``use_mocks=false`` pero sin ARN/endpoint, se conserva SQLite."""
    settings = Settings(environment="production", database_url="sqlite://")
    assert settings.resolve_database_url() == "sqlite://"


def test_resolve_url_mock_no_llama_boto3(monkeypatch: pytest.MonkeyPatch) -> None:
    """En modo mock, resolver la URL no debe tocar boto3 en absoluto."""
    import boto3

    def _boom(*_a, **_k):  # pragma: no cover - no debería invocarse
        raise AssertionError("boto3 no debe llamarse en modo mock")

    monkeypatch.setattr(boto3, "client", _boom)
    settings = Settings(
        environment="development",
        db_secret_arn="arn:aws:secretsmanager:...:secret:x",
        db_endpoint="host",
    )
    assert settings.resolve_database_url().startswith("sqlite")


# ---------------------------------------------------------------------------
# resolve_database_url: camino AWS → arma Postgres desde el secreto (boto3 mock)
# ---------------------------------------------------------------------------
def _fake_boto3_client(secret_payload: dict):
    """Devuelve un stub de ``boto3.client`` que entrega el secreto dado."""

    class _FakeSM:
        def __init__(self) -> None:
            self.pedido_id: str | None = None

        def get_secret_value(self, SecretId: str):  # noqa: N803 (API de boto3)
            self.pedido_id = SecretId
            return {"SecretString": json.dumps(secret_payload)}

    fake = _FakeSM()

    def _client(servicio: str, region_name: str | None = None):
        assert servicio == "secretsmanager"
        return fake

    return _client, fake


def test_resolve_url_camino_aws_arma_postgres_desde_secreto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import boto3

    client_stub, fake_sm = _fake_boto3_client(
        {"username": "jaimes_admin", "password": "sUp3r"}
    )
    monkeypatch.setattr(boto3, "client", client_stub)

    settings = Settings(
        environment="production",
        db_secret_arn="arn:aws:secretsmanager:us-east-1:123:secret:jaimes-abc",
        db_endpoint="cluster.rds.amazonaws.com",
        db_port=5432,
        db_name="jaimes",
    )
    url = settings.resolve_database_url()
    assert url == (
        "postgresql+psycopg://jaimes_admin:sUp3r@"
        "cluster.rds.amazonaws.com:5432/jaimes"
    )
    # Se leyó exactamente el secreto cuyo ARN se inyectó.
    assert fake_sm.pedido_id == (
        "arn:aws:secretsmanager:us-east-1:123:secret:jaimes-abc"
    )


def test_resolve_url_camino_aws_codifica_password_con_simbolos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import boto3

    client_stub, _ = _fake_boto3_client(
        {"username": "admin", "password": "p@ss/w:rd"}
    )
    monkeypatch.setattr(boto3, "client", client_stub)

    settings = Settings(
        environment="production",
        db_secret_arn="arn:secret",
        db_endpoint="h",
        db_port=5432,
        db_name="jaimes",
    )
    url = settings.resolve_database_url()
    assert "p%40ss%2Fw%3Ard" in url
    assert url.count("@") == 1


def test_aws_region_desde_alias_de_entorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``AWS_REGION_NAME`` (variable del stack) puebla ``aws_region``."""
    monkeypatch.setenv("AWS_REGION_NAME", "sa-east-1")
    # Evita que un ``.env`` o ``AWS_REGION`` del entorno interfiera.
    monkeypatch.delenv("AWS_REGION", raising=False)
    settings = Settings(_env_file=None)
    assert settings.aws_region == "sa-east-1"


def test_ai_enabled_se_carga_del_entorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_ENABLED", "true")
    settings = Settings(_env_file=None)

    assert settings.ai_enabled is True
    assert settings.use_bedrock is True
    assert settings.use_mocks is True
