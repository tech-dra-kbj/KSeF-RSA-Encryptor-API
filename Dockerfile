FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    WORKERS=3 \
    THREADS=2

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY swaggerapi.yaml encrypt_service.py pdf_generator_bridge.mjs ./
COPY core/ ./core/
COPY routes/ ./routes/
COPY pdf-generator/dist ./pdf-generator/dist

EXPOSE ${PORT}

CMD ["sh", "-c", "gunicorn --workers ${WORKERS} --threads ${THREADS} --preload --bind 0.0.0.0:${PORT} encrypt_service:app"]
