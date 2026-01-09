FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/VinculacionDigital/backend

# Dependencias de sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend /opt/VinculacionDigital/backend

ENV DJANGO_SETTINGS_MODULE=core.settings

CMD ["gunicorn", "core.wsgi:application", "--bind", "unix:/opt/VinculacionDigital/vinculaciondigital.sock", "--workers", "3"]
