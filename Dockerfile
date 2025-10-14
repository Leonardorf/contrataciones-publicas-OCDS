FROM python:3.11-slim

# Evitar bytecode y buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema mínimas (si en el futuro se requieren más, añadir aquí)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app

# Puerto por defecto
ENV PORT=8050 HOST=0.0.0.0

EXPOSE 8050

CMD ["gunicorn", "app.app:server", "--bind", "0.0.0.0:8050", "--workers", "2", "--timeout", "120"]