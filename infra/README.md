# jAImes — Infraestructura (AWS CDK, Python)

Infraestructura como Código del **Módulo H**. Una sola lengua para backend e
infraestructura: **AWS CDK en Python** (Requirement 10.1). Los stacks despliegan
la arquitectura serverless (API Gateway + Lambda con FastAPI/Mangum, Aurora
Serverless v2 + `pgvector`, S3, Bedrock, Transcribe, Textract, Rekognition,
Secrets Manager, CloudWatch).

> Arquitectura, stacks e IAM detallados: ver [`../docs/cloud/`](../docs/cloud/README.md)
> ([`cdk.md`](../docs/cloud/cdk.md), [`despliegue.md`](../docs/cloud/despliegue.md)).

La tarea **11.1** dejó el **tooling** y el **andamiaje** listos y
*sintetizables sin credenciales*. La tarea **11.2** añade los **cuatro stacks
reales** (`NetworkStack`, `DataStack`, `ComputeStack`, `AiIamStack`), que
``app.py`` cablea por cruce de referencias (el stack placeholder queda retirado
del cableado). El despliegue real es la tarea **11.3** (requiere credenciales).

## Estructura

```
infra/
  app.py                      # entrypoint de la cdk.App: instancia los 4 stacks
  cdk.json                    # config CDK: "app": "python app.py" + feature flags
  requirements.txt            # aws-cdk-lib + constructs (versiones fijadas)
  stacks/
    __init__.py               # exporta los 4 stacks reales
    network_stack.py          # NetworkStack: VPC mínima + endpoints de VPC
    data_stack.py             # DataStack: Aurora v2 (pgvector) + S3 cifrado + secretos
    compute_stack.py          # ComputeStack: Lambda (FastAPI+Mangum) + HTTP API
    ai_iam_stack.py           # AiIamStack: IAM mínimos (Bedrock/Transcribe/Textract/Rekognition)
    placeholder_stack.py      # andamiaje 11.1 (ya no se usa; se conserva como referencia)
  .gitignore                  # ignora cdk.out/, .venv/, __pycache__/
```

### Composición de los stacks (cruce de referencias)

```
NetworkStack ── vpc ──▶ DataStack ── vpc, cluster, secreto, bucket, SG ──▶ ComputeStack
                                                                              │ rol Lambda
                                                                              ▼
                                                                           AiIamStack
```

- `NetworkStack` crea la VPC mínima (2 AZ, subredes privadas aisladas, sin NAT)
  con endpoints de VPC: S3 (gateway) y Secrets Manager / Bedrock runtime /
  CloudWatch Logs (interface).
- `DataStack` crea Aurora Serverless v2 (PostgreSQL 15.4 + `pgvector`), el bucket
  S3 cifrado (SSE-S3, sin acceso público, SSL forzado) y el secreto de
  credenciales en Secrets Manager. Define el SG cliente de la Lambda y autoriza
  su ingreso al puerto 5432 de Aurora *dentro de este stack* (evita ciclos).
- `ComputeStack` crea la Lambda (handler `app.main.handler`, `USE_MOCKS=false`)
  tras un HTTP API de API Gateway, con acceso de mínimos privilegios al bucket y
  al secreto.
- `AiIamStack` adjunta al rol de la Lambda los permisos mínimos de IA.

### Empaquetado de la Lambda

Por defecto, el código se empaqueta como *asset* del directorio `backend/` **sin
bundling**, de modo que `cdk synth` corra **offline y sin Docker**. Para instalar
las dependencias de `backend/requirements.txt` en el artefacto durante el deploy,
exporta `CDK_BUNDLE=1` antes de `cdk deploy` (requiere Docker); alternativa sin
Docker: una capa (*layer*) de dependencias. Este paso solo se valida en el deploy
real (tarea 11.3).

## ⚠️ Prerrequisito del usuario: credenciales AWS

Antes de **desplegar** (`cdk bootstrap`, `cdk deploy`) o correr la integración
cloud real, configura las credenciales de la **cuenta de la hackathon**:

```bash
aws configure
# AWS Access Key ID / Secret Access Key / región (p. ej. us-east-1) / formato
```

Sin credenciales todo lo demás funciona en modo mock (`USE_MOCKS=true`) y
`cdk synth` corre igual (es agnóstico de entorno). Solo `cdk bootstrap` y
`cdk deploy` exigen credenciales.

## 1. Instalar el tooling

### AWS CLI v2

- **Windows:** instalar el MSI oficial de *AWS CLI v2*, o `winget install Amazon.AWSCLI`.
- **macOS:** `brew install awscli` (v2) o el instalador `.pkg` oficial.
- **Linux:** descargar el zip oficial de *AWS CLI v2* y ejecutar su `./install`.

Verificar: `aws --version` (debe reportar `aws-cli/2.x`).

### AWS CDK (Toolkit)

El CDK Toolkit (comando `cdk`) se distribuye vía npm (requiere Node.js ≥ 18):

```bash
npm install -g aws-cdk
cdk --version
```

> Alternativa sin instalar global: `npx aws-cdk@2 <comando>`.

### Dependencias Python del proyecto CDK

Desde `infra/`, en un entorno virtual propio:

```bash
cd infra
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

## 2. Sintetizar (sin credenciales)

Valida que el proyecto compila y genera CloudFormation. **No requiere AWS**:

```bash
cdk synth
```

Debe sintetizar los cuatro stacks (`JaimesNetworkStack`, `JaimesDataStack`,
`JaimesComputeStack`, `JaimesAiIamStack`) sin errores. Si no tienes `cdk`
global, usa `npx aws-cdk@2 synth` (apuntando al Python del venv con
`--app ".venv/bin/python app.py"` en entornos donde `cdk.json` no resuelva el
intérprete del venv).

## 3. Bootstrap y despliegue (requiere credenciales)

Tras `aws configure`:

```bash
cdk bootstrap           # una sola vez por cuenta/región
cdk deploy --all        # despliega los stacks (reales a partir de la tarea 11.2)
```

Si `cdk deploy` falla, CDK/CloudFormation reporta el stack y recurso que causó
el fallo y deja el entorno reintentar-able (Requirement 10.5).

## Verificación rápida

| Comando | Qué confirma |
|---|---|
| `aws --version` | AWS CLI v2 instalada |
| `cdk --version` | CDK Toolkit instalado |
| `cdk synth` | El proyecto CDK compila y sintetiza (offline) |
| `cdk bootstrap` / `cdk deploy` | Despliegue real (requiere `aws configure`) |
