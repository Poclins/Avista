# Despliegue AWS MVP

Este despliegue crea únicamente `JaimesMvpStack`: una Lambda x86_64 basada en la imagen del `Dockerfile` raíz y una Function URL pública que sirve FastAPI y la PWA en el mismo origen. No crea API Gateway, VPC, RDS, S3, CloudFront, ECS ni Secrets Manager, y no modifica ni destruye stacks anteriores.

## Prerrequisitos

- Windows PowerShell, Docker Desktop iniciado, AWS CLI v2 y AWS CDK en `PATH`.
- Sesión AWS vigente en la cuenta `655275680575`, región configurada `us-east-1` y `CDKToolkit` desplegado.
- No se necesitan ni deben copiarse API keys o archivos `.env`.

```powershell
python -m venv .\infra\.venv
& .\infra\.venv\Scripts\python.exe -m pip install -r .\infra\requirements.txt
& .\infra\.venv\Scripts\python.exe -m pytest .\infra\tests
powershell -ExecutionPolicy Bypass -File .\deployment\deploy_mvp.ps1
```

`deploy_mvp.ps1` ejecuta primero preflight de identidad, cuenta, región, bootstrap, CDK y Docker. Solo después sintetiza y despliega explícitamente `JaimesMvpStack`; la URL queda en `infra/cdk-outputs.json`.

## Smoke cloud

```powershell
powershell -ExecutionPolicy Bypass -File .\deployment\verify_mvp.ps1 `
  -OutputsFile .\infra\cdk-outputs.json `
  -AudioPath .\audio_testing\test1.mp3
```

El smoke comprueba `/health`, la PWA y la API en el mismo origen; elige una educadora y un niño relacionados; transcribe el MP3 con Nova Sonic mediante IAM; confirma la clasificación de Claude; y genera una bitácora mediante Claude. También consulta y reporta los stacks anteriores sin alterarlos.

## Restricciones del MVP

La base SQLite y los medios viven en `/tmp`, por lo que los datos sobreviven solo mientras se reutiliza el entorno Lambda y un cold start nuevo puede restaurar el seed limpio. La Function URL usa `AuthType.NONE` para la demo y la concurrencia reservada se limita a 5. Los permisos de la función se restringen a invocaciones Bedrock requeridas, sobre `Resource *` porque los modelos se resuelven en runtime.
