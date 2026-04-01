FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    WORKERS=3 \
    THREADS=2

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY swaggerapi.yaml encrypt_service.py pdf_generator_bridge.mjs .
COPY pdf-generator/dist ./pdf-generator/dist

EXPOSE ${PORT}

CMD ["gunicorn", "--workers", "3", "--threads", "2", "--bind", "0.0.0.0:5000", "encrypt_service:app"]
