# jAImes — De la observación a la acción

IA para el desarrollo infantil · **Fundación Integra** · desafío *"IA para el
Desarrollo Infantil"*, **AWS Breaking Barriers Chile 2026**.

jAImes convierte los recursos crudos que ya generan las educadoras de párvulos
(texto, fotos de notas manuscritas, audios, videos) en observaciones
estructuradas, trayectorias de desarrollo, bitácoras quincenales,
recomendaciones de nivel y reportes de dirección — reduciendo el tiempo de
documentación de ~4 h/semana hacia ~0.

> ⚠️ Datos **sintéticos y seudonimizados** (dataset E-1). No es instrumento
> clínico ni diagnóstico.

## Arquitectura (3 capas)

```
Capa 1 · Presentación      → frontend/  (React + Vite PWA, solo UI + REST)
Capa 2 · Lógica de negocio → backend/app/api → services → domain → providers
Capa 3 · Acceso a datos    → backend/app/repositories (relacional, vectorial, storage)
Infra externa              → AWS (Transcribe/Textract/Rekognition/Bedrock/Titan/S3)
                             o mocks locales
```

La IA se integra con **puertos y adaptadores**: cada capacidad
(`TranscriptionProvider`, `EmbeddingProvider`, `LlmProvider`) y cada repositorio
tiene una interfaz con implementaciones AWS y mock intercambiables. El flag
`USE_MOCKS` decide cuál se usa, de modo que la demo corre **sin credenciales
AWS**.

### Estructura del repositorio

```
backend/
  app/
    api/routers/     routers REST (se añaden en tareas posteriores)
    services/        casos de uso
    domain/          modelos POO + rúbrica determinista
    providers/       puertos de IA + adaptadores AWS/mock
    repositories/    acceso a datos relacional/vectorial/storage
    core/            config.py (settings) + contenedor de DI
    main.py          app FastAPI (health check)
  tests/             tests (smoke del scaffolding)
  requirements.txt   dependencias de ejecución
  Dockerfile         imagen del backend
frontend/            PWA (placeholder; se inicializa en la tarea 14)
docker-compose.yml   backend + Postgres/pgvector (un solo comando)
```

## Ejecución con Docker (un solo comando)

Requiere Docker y Docker Compose.

```bash
docker-compose up --build
```

Esto levanta:
- **backend** en http://localhost:8000 (health check en `/health`, docs en `/docs`),
- **db**: Postgres 16 con la extensión `pgvector`.

El backend arranca en **modo mock** (`USE_MOCKS=true`) por defecto, así la demo
funciona aunque no haya red ni credenciales AWS.

## Desarrollo local (sin Docker)

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env          # ajustar si hace falta (Windows: copy)

uvicorn app.main:app --reload
```

Abre http://localhost:8000/health y http://localhost:8000/docs.

### Tests

```bash
cd backend
pytest
```

## Modo mock vs AWS

| `USE_MOCKS` | Providers de IA     | Base relacional   | Base vectorial         | Storage          |
| ----------- | ------------------- | ----------------- | ---------------------- | ---------------- |
| `true`      | respuestas mock     | SQLite local      | índice en memoria      | disco local      |
| `false`     | AWS (Transcribe, Textract, Rekognition, Bedrock, Titan) | Postgres/RDS | pgvector | S3 |

Para usar AWS real, en `backend/.env` define `USE_MOCKS=false` y completa
`AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `DATABASE_URL`
(Postgres, dialecto `postgresql+psycopg://`). Las mismas interfaces se
mantienen; solo cambia el adaptador que el
contenedor de DI construye (Requirement 10.4).

## Estado

Scaffolding y configuración base (Tarea 1). Los modelos de dominio, servicios,
repositorios, API y el frontend se implementan en las tareas siguientes del
plan en `.kiro/specs/jaimes-mvp/`.