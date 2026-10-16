"""ComputeStack — cómputo serverless de jAImes: Lambda (FastAPI+Mangum) + HTTP API.

Módulo H (AWS CDK en Python). Provisiona la **capa 2** (lógica de negocio) de la
arquitectura serverless siguiendo ``docs/cloud/cdk.md``:

- **AWS Lambda** que ejecuta *el mismo* FastAPI que corre en local, envuelto por
  Mangum. El handler es ``app.main.handler`` (ver ``backend/app/main.py``:
  ``handler = Mangum(app)``). El mismo artefacto y el mismo contenedor de DI
  sirven en Lambda y en ``uvicorn``; la diferencia la marca solo la
  configuración (``USE_MOCKS``).
- **Amazon API Gateway HTTP API** como front del endpoint REST, con la Lambda
  como integración *proxy* (``$default``), de modo que todas las rutas de
  FastAPI (incl. ``/health``) queden detrás de un único proxy.
- **Variables de entorno** que seleccionan el camino AWS real
  (``USE_MOCKS=false``) e inyectan los recursos de `DataStack` (endpoint y
  secreto de Aurora, bucket S3, región, IDs de modelos Bedrock).
- **IAM de mínimos privilegios** sobre los recursos de datos: la Lambda recibe
  solo lectura/escritura del bucket de medios y lectura del secreto de BD
  (Requirement 11.6). Los permisos de IA (Bedrock/Transcribe/Textract/
  Rekognition) los añade `AiIamStack` sobre ``self.lambda_fn.role``.
- **CloudWatch**: la Lambda registra en su log group gestionado (retención
  acotada para el MVP).

### Empaquetado de la Lambda (decisión documentada)

El código se toma como *asset* del directorio ``backend/`` del repo, con dos
modos (ver :func:`_lambda_code`):

- **Por defecto** (``cdk synth`` offline): se empaqueta el directorio sin
  *bundling*. Sintetiza sin Docker ni red, clave para validar la plantilla sin
  credenciales.
- **Con ``CDK_BUNDLE=1``** (``cdk deploy``): se instalan las dependencias de
  ``backend/requirements.txt`` (fastapi, mangum, boto3, psycopg[binary], …) en
  el *staging* del asset mediante *bundling* con la imagen oficial de Lambda
  Python 3.12. Alternativa sin Docker: una capa (*layer*) de dependencias.

El empaquetado con dependencias solo es verificable en el *deploy* real
(tarea 11.3): ``cdk synth`` valida la plantilla, no construye el artefacto final.
"""

from __future__ import annotations

import os
from pathlib import Path

from aws_cdk import BundlingOptions, CfnOutput, CustomResource, Duration, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as apigwv2_integrations
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import custom_resources as cr
from constructs import Construct

# Ruta al backend (repo_root/backend) desde infra/stacks/compute_stack.py.
_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"

# Comando de bundling: instala requirements y copia el código al artefacto.
# Solo se ejecuta en el staging del asset (deploy con bundling habilitado).
_BUNDLING_COMMAND = (
    "pip install -r requirements.txt -t /asset-output && "
    "cp -au app /asset-output"
)


def _lambda_code() -> lambda_.AssetCode:
    """Empaquetado del código de la Lambda (asset del directorio ``backend/``).

    Dos modos, por diseño (ver docstring del stack):

    - **Por defecto (``cdk synth`` offline):** se toma el directorio ``backend/``
      tal cual, sin *bundling*. Sintetiza sin Docker ni red (clave para validar
      la plantilla sin credenciales). El artefacto no incluye aún las
      dependencias de ``requirements.txt``.
    - **Con ``CDK_BUNDLE=1`` (``cdk deploy`` con Docker):** se instalan las
      dependencias en el *staging* del asset con la imagen oficial de Lambda
      Python 3.12. Este paso solo es verificable en el *deploy* real
      (tarea 11.3). Alternativa sin Docker: una capa (*layer*) de dependencias.
    """
    if os.environ.get("CDK_BUNDLE") == "1":
        return lambda_.Code.from_asset(
            str(_BACKEND_DIR),
            bundling=BundlingOptions(
                image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                command=["bash", "-c", _BUNDLING_COMMAND],
            ),
        )
    return lambda_.Code.from_asset(str(_BACKEND_DIR))


class ComputeStack(Stack):
    """Lambda (FastAPI+Mangum) tras un HTTP API de API Gateway."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        database: rds.DatabaseCluster,
        db_secret: secretsmanager.ISecret,
        media_bucket: s3.IBucket,
        lambda_security_group: ec2.ISecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Variables de entorno compartidas por la Lambda del API y la Lambda de
        # seed: ambas usan el *mismo* backend (mismo contenedor de DI) y, por
        # tanto, la misma configuración de recursos de datos. Centralizarlas
        # evita que las dos funciones diverjan en su acceso a Aurora/S3.
        shared_environment = {
            # Camino AWS real: adaptadores reales, no mocks.
            "USE_MOCKS": "false",
            "ENVIRONMENT": "production",
            # Recursos de datos inyectados desde DataStack.
            "AWS_REGION_NAME": self.region,
            "S3_BUCKET": media_bucket.bucket_name,
            "DB_SECRET_ARN": db_secret.secret_arn,
            "DB_ENDPOINT": database.cluster_endpoint.hostname,
            "DB_PORT": str(database.cluster_endpoint.port),
            "DB_NAME": "jaimes",
            # IDs de modelos Bedrock (coinciden con los por defecto del
            # backend; se dejan explícitos para el camino AWS).
            "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "TITAN_EMBEDDING_MODEL_ID": "amazon.titan-embed-text-v2:0",
        }

        # ------------------------------------------------------------------
        # Función Lambda: FastAPI + Mangum, in-VPC para alcanzar Aurora.
        # ------------------------------------------------------------------
        self.lambda_fn = lambda_.Function(
            self,
            "JaimesApi",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="app.main.handler",  # Mangum(app) en backend/app/main.py
            code=_lambda_code(),
            memory_size=1024,
            timeout=Duration.seconds(30),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            # SG definido en DataStack (ya autorizado en el puerto de Aurora),
            # para no crear una referencia cíclica entre stacks.
            security_groups=[lambda_security_group],
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment=dict(shared_environment),
        )

        # ------------------------------------------------------------------
        # IAM de mínimos privilegios sobre los recursos de datos.
        # ------------------------------------------------------------------
        # Lectura/escritura del bucket de medios (subir/leer observaciones).
        media_bucket.grant_read_write(self.lambda_fn)
        # Lectura del secreto de credenciales de BD (Requirement 11.6).
        db_secret.grant_read(self.lambda_fn)
        # El acceso de red a Aurora (puerto 5432) ya está autorizado en
        # DataStack mediante el security group `lambda_security_group`, que
        # esta Lambda lleva adjunto. No se añade regla aquí para evitar el
        # ciclo DataStack <-> ComputeStack.

        # ------------------------------------------------------------------
        # API Gateway HTTP API con la Lambda como integración proxy ($default).
        # ------------------------------------------------------------------
        self.http_api = apigwv2.HttpApi(
            self,
            "JaimesHttpApi",
            description="HTTP API de jAImes (proxy a FastAPI/Mangum en Lambda)",
            default_integration=apigwv2_integrations.HttpLambdaIntegration(
                "JaimesLambdaIntegration",
                handler=self.lambda_fn,
            ),
        )

        # ------------------------------------------------------------------
        # Lambda de SEED (in-VPC) + custom resource que la invoca en el deploy.
        # ------------------------------------------------------------------
        # Aurora vive en subredes privadas aisladas (sin NAT ni acceso público;
        # ver DataStack), por lo que no puede sembrarse desde la máquina local.
        # Esta Lambda dedicada reutiliza el *mismo* asset de backend y corre en
        # la *misma* VPC/subredes/SG que la Lambda del API (mismo acceso a
        # Aurora y lectura del mismo secreto), ejecutando el seed del Dataset
        # E-1 (``app.seed_handler.handler``). No cambia la topología de red ni
        # debilita los security groups: solo añade una función cliente más
        # detrás del SG ya autorizado al puerto 5432.
        self.seed_fn = lambda_.Function(
            self,
            "JaimesSeed",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="app.seed_handler.handler",
            code=_lambda_code(),
            memory_size=1024,
            # El seed carga el dataset y crea el esquema + pgvector; se da un
            # margen amplio (muy por debajo del coste real del dataset reducido).
            timeout=Duration.minutes(5),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            # Mismo SG cliente de Aurora que la Lambda del API: mismo acceso de
            # red al puerto 5432 ya autorizado en DataStack (sin reglas nuevas).
            security_groups=[lambda_security_group],
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment=dict(shared_environment),
        )
        # La Lambda de seed necesita leer el secreto de credenciales de Aurora
        # (mismo mínimo privilegio que el API: solo lectura del secreto).
        db_secret.grant_read(self.seed_fn)

        # Provider framework de CDK: envuelve la Lambda de seed como un custom
        # resource de CloudFormation que se invoca **una vez** en Create/Update
        # del stack. El framework envía la respuesta a CFN según el handler
        # retorne (éxito) o lance (fallo), dejando el deploy reintentar-able.
        seed_provider = cr.Provider(
            self,
            "JaimesSeedProvider",
            on_event_handler=self.seed_fn,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )
        seed_resource = CustomResource(
            self,
            "JaimesSeedResource",
            service_token=seed_provider.service_token,
            # Cambiar este valor en un deploy futuro vuelve a disparar el seed
            # (idempotente). Hoy fija la primera siembra del Dataset E-1.
            properties={"version": "e1-seed-1"},
        )
        # El seed solo puede correr cuando la Lambda del API/su integración ya
        # existen y Aurora está disponible; CDK infiere la dependencia de datos
        # por las env vars, pero fijamos el orden explícitamente para el API.
        seed_resource.node.add_dependency(self.lambda_fn)

        # URL base del API (útil para verificar GET /health tras el deploy).
        CfnOutput(
            self,
            "ApiUrl",
            value=self.http_api.api_endpoint,
            description=(
                "URL base del HTTP API de jAImes. Verificar GET /health "
                "(HTTP 200) tras el deploy (tarea 11.3)."
            ),
        )
