FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app/backend

RUN apt-get update     && apt-get install -y --no-install-recommends build-essential curl     && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip setuptools wheel     && pip install --no-cache-dir -e /app/backend

COPY backend /app/backend

RUN chmod +x /app/backend/scripts/docker-api-entrypoint.sh /app/backend/scripts/docker-worker-entrypoint.sh
