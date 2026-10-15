"""Configuración central de jAImes.

Lee variables de entorno (y un archivo ``.env`` si existe) mediante
``pydantic-settings``. El flag ``USE_MOCKS`` es el interruptor principal del
modo demo: cuando es ``true`` el contenedor de DI construye adaptadores mock
(sin AWS) y repositorios locales (SQLite + índice en memoria); cuando es
``false`` y hay credenciales AWS, usa los servicios reales a través de las
mismas interfaces (Requirements 10.1 y 10.4).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de la aplicación poblados desde el entorno/.env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicación ---
    app_name: str = "jAImes"
    environment: str = "development"
    debug: bool = True

    # --- Modo demo / selección de adaptadores ---
    # true  -> providers y storage mock (sin AWS), repos locales.
    # false -> servicios AWS reales a través de las mismas interfaces.
    use_mocks: bool = True

    # --- Base de datos relacional ---
    # En modo mock se usa SQLite; en AWS, Postgres/pgvector (RDS/Aurora).
    database_url: str = "sqlite:///./jaimes.db"

    # --- Almacenamiento de objetos ---
    s3_bucket: str = "jaimes-media"
    local_storage_dir: str = "./storage"

    # --- AWS ---
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # Identificadores de modelos AWS (solo relevantes con use_mocks=false)
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    titan_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    @property
    def is_mock_mode(self) -> bool:
        """Atajo semántico para ``use_mocks``."""
        return self.use_mocks


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de :class:`Settings`.

    Se usa como dependencia de FastAPI (``Depends(get_settings)``) para que
    toda la aplicación comparta la misma configuración.
    """
    return Settings()
