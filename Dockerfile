FROM node:20.18.1-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM public.ecr.aws/lambda/python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=development \
    AI_ENABLED=true \
    DATABASE_URL=sqlite:////tmp/jaimes.db \
    DEMO_SEED_DB_PATH=/var/task/resources/jaimes_seed.db \
    DATASET_ZIP_PATH=/var/task/resources/dataset_e1_publico.zip \
    LOCAL_STORAGE_DIR=/tmp/storage \
    FRONTEND_DIST_PATH=/var/task/frontend/dist \
    AWS_REGION_NAME=us-east-1 \
    BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-5 \
    NOVA_SONIC_MODEL_ID=amazon.nova-2-sonic-v1:0

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --target "${LAMBDA_TASK_ROOT}" -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY backend/app "${LAMBDA_TASK_ROOT}/app"
COPY backend/dataset_e1_publico.zip "${LAMBDA_TASK_ROOT}/resources/dataset_e1_publico.zip"
COPY --from=frontend-build /build/frontend/dist "${LAMBDA_TASK_ROOT}/frontend/dist"

RUN DATABASE_URL=sqlite:////var/task/resources/jaimes_seed.db \
    DATASET_ZIP_PATH=/var/task/resources/dataset_e1_publico.zip \
    python -m app.repositories.seed.seed

CMD ["app.main.handler"]
