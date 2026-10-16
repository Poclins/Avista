"""ConfiguraciÃ³n central de jAImes.

Lee variables de entorno (y un archivo ``.env`` si existe) mediante
``pydantic-settings``. El flag ``USE_MOCKS`` es el interruptor principal del
modo demo: cuando es ``true`` el contenedor de DI construye adaptadores mock
(sin AWS) y repositorios locales (SQLite + Ã­ndice en memoria); cuando es
``false`` y hay credenciales AWS, usa los servicios reales a travÃ©s de las
mismas interfaces (Requirements 10.1 y 10.4).
"""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de la aplicaciÃ³n poblados desde el entorno/.env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    # --- AplicaciÃ³n ---
    app_name: str = "jAImes"
    environment: str = "development"
    debug: bool = True

    # --- Modo demo / selecciÃ³n de adaptadores ---
    # true  -> providers y storage mock (sin AWS), repos locales.
    # false -> servicios AWS reales a travÃ©s de las mismas interfaces.

    # --- Base de datos relacional ---
    # En modo mock se usa SQLite; en AWS, Postgres/pgvector (RDS/Aurora).
    # En AWS la URL **no** se fija aquÃ­: se arma en runtime desde el secreto de
    # Secrets Manager (``db_secret_arn``) + los datos de conexiÃ³n que inyecta
    # ``ComputeStack`` (``db_endpoint``/``db_port``/``db_name``). Ver
    # :meth:`resolve_database_url`.
    database_url: str = "sqlite:///./jaimes.db"

    # --- ConexiÃ³n a Aurora (inyectada por ComputeStack en Lambda) ---
    # El ARN del secreto de credenciales de Aurora en Secrets Manager; cuando
    # estÃ¡ presente y ``use_mocks=false``, la URL de BD se arma leyÃ©ndolo.
    db_secret_arn: str | None = None
    db_endpoint: str | None = None
    db_port: int = 5432
    db_name: str = "jaimes"

    # --- Dataset E-1 oficial (seed) ---
    # Ruta al zip pÃºblico del Dataset E-1 oficial (7 CSV + consolidado.json).
    # Si estÃ¡ presente, el seed carga vÃ­a ``DatasetLoader`` (fuente de verdad);
    # si no, cae al dataset reducido/casero (solo respaldo rÃ¡pido de pruebas).
    dataset_zip_path: str = "./dataset_e1_publico.zip"

    # --- Almacenamiento de objetos ---
    s3_bucket: str = "jaimes-media"
    local_storage_dir: str = "./storage"

    # --- AWS ---
    # Acepta tanto ``AWS_REGION`` (que Lambda inyecta automÃ¡ticamente) como
    # ``AWS_REGION_NAME`` (la variable que define ``ComputeStack``), ademÃ¡s del
    # nombre de campo ``aws_region``.
    aws_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices(
            "aws_region", "AWS_REGION_NAME", "AWS_REGION"
        ),
    )
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # Clave Bearer de Bedrock para usar el LLM real manteniendo SQLite local.
    bedrock_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "bedrock_api_key", "AWS_BEARER_TOKEN_BEDROCK"
        ),
    )

    # Campo opcional separado para Nova Sonic. Si queda vacío se reutiliza la
    # API key general de Bedrock, porque ambas pertenecen al mismo servicio.
    nova_sonic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "nova_sonic_api_key", "NOVA_SONIC_API_KEY"
        ),
    )
    # Identificadores de modelos AWS (solo relevantes con use_mocks=false)
    bedrock_model_id: str = "global.anthropic.claude-sonnet-5"
    nova_sonic_model_id: str = "amazon.nova-2-sonic-v1:0"
    nova_sonic_max_seconds: int = 60
    titan_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    @property
    def bedrock_api_key_value(self) -> str | None:
        """Devuelve la clave Bedrock sin exponerla en repr ni logs."""
        if self.bedrock_api_key is None:
            return None
        valor = self.bedrock_api_key.get_secret_value().strip()
        return valor or None

    @property
    def nova_sonic_api_key_value(self) -> str | None:
        """Clave específica de Sonic o, si no existe, la clave Bedrock común."""
        if self.nova_sonic_api_key is not None:
            valor = self.nova_sonic_api_key.get_secret_value().strip()
            if valor:
                return valor
        return self.bedrock_api_key_value
    @property
    def use_bedrock(self) -> bool:
        """Usa Bedrock si hay API key o si el entorno es producción."""
        return bool(self.bedrock_api_key_value) or not self.use_mocks
    @property
    def use_mocks(self) -> bool:
        """Indica si se usan proveedores locales deterministas.

        Es una propiedad derivada, no una variable de entorno. Desarrollo es
        local por defecto; el camino AWS se activa con ENVIRONMENT=production.
        """
        return self.environment.strip().lower() != "production"

    @property
    def is_mock_mode(self) -> bool:
        """Alias semántico del modo local."""
        return self.use_mocks

    @property
    def _usa_aurora_desde_secreto(self) -> bool:
        """Â¿Debe armarse la URL de BD desde el secreto de Aurora?

        Solo en el camino AWS real (``ENVIRONMENT=production``) y cuando
        ``ComputeStack`` inyectÃ³ el ARN del secreto y el endpoint del cluster.
        En modo mock (o sin esos datos) se conserva la ``database_url`` por
        defecto (SQLite), de modo que importar la config no exija red ni
        credenciales.
        """
        return (
            not self.use_mocks
            and bool(self.db_secret_arn)
            and bool(self.db_endpoint)
        )

    def resolve_database_url(self) -> str:
        """Devuelve la URL de BD efectiva, armÃ¡ndola desde Secrets Manager si aplica.

        - **Modo mock / sin datos de Aurora:** devuelve ``database_url`` tal
          cual (SQLite por defecto). No toca red ni credenciales.
        - **Camino AWS (producción + ``db_secret_arn`` + ``db_endpoint``):**
          lee el secreto JSON de Aurora (``username``/``password``) vÃ­a boto3 y
          construye una URL ``postgresql+psycopg://USER:PASS@ENDPOINT:PORT/NAME``.

        La lectura es **perezosa**: solo ocurre al llamar a este mÃ©todo (que el
        contenedor de DI invoca al crear el engine), nunca al importar la
        configuraciÃ³n. Mantiene el diseÃ±o perezoso del contenedor.
        """
        if not self._usa_aurora_desde_secreto:
            return self.database_url
        usuario, clave = self._leer_credenciales_secreto()
        return construir_url_postgres(
            usuario=usuario,
            clave=clave,
            host=self.db_endpoint or "",
            puerto=self.db_port,
            base=self.db_name,
        )

    def _leer_credenciales_secreto(self) -> tuple[str, str]:
        """Lee ``username``/``password`` del secreto de Aurora en Secrets Manager.

        Import diferido de boto3: solo se necesita en el camino AWS. El secreto
        es un JSON con, al menos, ``username`` y ``password`` (formato estÃ¡ndar
        de los secretos de credenciales de RDS/Aurora).
        """
        import boto3  # import diferido: solo en el camino AWS.

        cliente = boto3.client("secretsmanager", region_name=self.aws_region)
        respuesta = cliente.get_secret_value(SecretId=self.db_secret_arn)
        datos = json.loads(respuesta["SecretString"])
        return str(datos["username"]), str(datos["password"])


def construir_url_postgres(
    *,
    usuario: str,
    clave: str,
    host: str,
    puerto: int,
    base: str,
) -> str:
    """Arma una URL SQLAlchemy ``postgresql+psycopg://`` segura.

    Usuario y clave se **codifican** (``quote_plus``) para que caracteres
    especiales en las credenciales (``@``, ``:``, ``/``, â€¦) no rompan ni
    "inyecten" partes de la URL. El driver es ``psycopg`` (v3), que el backend
    ya declara como dependencia (``psycopg[binary]``).
    """
    from urllib.parse import quote_plus

    usuario_q = quote_plus(usuario)
    clave_q = quote_plus(clave)
    return (
        f"postgresql+psycopg://{usuario_q}:{clave_q}@{host}:{puerto}/{base}"
    )


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de :class:`Settings`.

    Se usa como dependencia de FastAPI (``Depends(get_settings)``) para que
    toda la aplicaciÃ³n comparta la misma configuraciÃ³n.
    """
    return Settings()

