"""Smoke tests del scaffolding: la app importa, arranca y la config carga."""

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_health_endpoint_responde_ok() -> None:
    """El health check responde 200 y expone el modo de ejecución."""
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "jAImes"
    assert "use_mocks" in body


def test_settings_default_use_mocks_true() -> None:
    """Por defecto el sistema corre en modo demo (sin AWS)."""
    settings = Settings()

    assert settings.use_mocks is True
    assert settings.is_mock_mode is True


def test_get_settings_devuelve_misma_instancia() -> None:
    """``get_settings`` está cacheado: una sola config compartida."""
    assert get_settings() is get_settings()


def test_frontend_estatico_no_intercepta_health(tmp_path) -> None:
    from app.main import create_app

    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text(
        "<html><body>jAImes PWA</body></html>",
        encoding="utf-8",
    )
    static_app = create_app(
        Settings(_env_file=None, frontend_dist_path=str(frontend))
    )
    static_client = TestClient(static_app)

    health = static_client.get("/health")
    root = static_client.get("/")

    assert health.status_code == 200
    assert health.headers["content-type"].startswith("application/json")
    assert health.json()["status"] == "ok"
    assert root.status_code == 200
    assert root.headers["content-type"].startswith("text/html")
    assert "jAImes PWA" in root.text
