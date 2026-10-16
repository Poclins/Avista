"""Punto de entrada de la app CDK de jAImes (Infraestructura como Código).

Módulo H — Infraestructura AWS serverless con **AWS CDK en Python** (una sola
lengua para backend e infraestructura; Requirement 10.1).

Este archivo es el *entrypoint* que `cdk` ejecuta (ver ``app`` en ``cdk.json``):
instancia la ``cdk.App`` y registra los cuatro stacks reales descritos en
``docs/cloud/cdk.md``, cableándolos por **cruce de referencias**:

```
NetworkStack ── vpc ──▶ DataStack ── vpc, cluster, secreto, bucket ──▶ ComputeStack
                                                                           │ rol Lambda
                                                                           ▼
                                                                        AiIamStack
```

- `NetworkStack` crea la VPC mínima; `DataStack` y `ComputeStack` la reciben.
- `DataStack` crea Aurora (pgvector), el bucket S3 cifrado y el secreto;
  `ComputeStack` los recibe para inyectarlos como env vars y conceder acceso
  de mínimos privilegios.
- `ComputeStack` crea la Lambda (FastAPI+Mangum) y el HTTP API; expone el rol
  de ejecución de la Lambda.
- `AiIamStack` adjunta a ese rol los permisos mínimos de IA
  (Bedrock/Transcribe/Textract/Rekognition).

Despliegue real: requiere credenciales AWS (`aws configure`) — prerrequisito
del usuario (ver ``README.md``). ``cdk synth`` funciona sin credenciales.
"""

from __future__ import annotations

import os

import aws_cdk as cdk

from stacks.ai_iam_stack import AiIamStack
from stacks.compute_stack import ComputeStack
from stacks.data_stack import DataStack
from stacks.network_stack import NetworkStack

app = cdk.App()

# El entorno (cuenta/región) se toma del perfil de credenciales configurado con
# `aws configure` (CDK_DEFAULT_ACCOUNT / CDK_DEFAULT_REGION). Si no hay
# credenciales, queda ``None`` y `cdk synth` sigue funcionando (agnóstico de
# entorno); solo `cdk deploy` exige credenciales.
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

# --- 1) Red: VPC mínima + endpoints de VPC. ---
network = NetworkStack(
    app,
    "JaimesNetworkStack",
    env=env,
    description="jAImes · red mínima (VPC + endpoints de VPC) para la pila serverless.",
)

# --- 2) Datos: Aurora Serverless v2 (pgvector), S3 cifrado, Secrets Manager. ---
data = DataStack(
    app,
    "JaimesDataStack",
    env=env,
    vpc=network.vpc,
    description="jAImes · capa de datos (Aurora pgvector + S3 cifrado + secretos).",
)

# --- 3) Cómputo: Lambda (FastAPI+Mangum) + HTTP API; USE_MOCKS=false. ---
compute = ComputeStack(
    app,
    "JaimesComputeStack",
    env=env,
    vpc=network.vpc,
    database=data.database,
    db_secret=data.db_secret,
    media_bucket=data.media_bucket,
    lambda_security_group=data.lambda_security_group,
    description="jAImes · cómputo serverless (Lambda FastAPI/Mangum + HTTP API).",
)

# --- 4) IAM de IA: permisos mínimos sobre el rol de la Lambda. ---
AiIamStack(
    app,
    "JaimesAiIamStack",
    env=env,
    lambda_role=compute.lambda_fn.role,
    description="jAImes · IAM de mínimos privilegios (Bedrock/Transcribe/Textract/Rekognition).",
)

app.synth()
