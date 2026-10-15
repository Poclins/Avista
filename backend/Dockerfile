# jAImes backend — imagen de la API FastAPI
FROM python:3.12-slim

# No generar .pyc y salida sin buffer (logs inmediatos)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias primero (mejor cache de capas).
# psycopg[binary] trae wheels self-contained, no requiere libpq/gcc.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
