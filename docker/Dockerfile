FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    WORKERS=3 \
    THREADS=2

WORKDIR /app

# Node stays — the PDF generator bridge runs on it. curl does not: it is only
# needed here to fetch the NodeSource setup script, so it is purged together
# with libcurl once Node is installed. Nothing in the running image links
# libcurl (it is an rdepend of curl alone) and the healthcheck goes through
# Python's urllib, so keeping curl would only add scan surface. apt-get
# upgrade picks up security updates published after the base image was cut.
RUN set -eux \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get upgrade -y \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY swaggerapi.yaml encrypt_service.py pdf_generator_bridge.mjs ./
COPY core/ ./core/
COPY routes/ ./routes/
COPY pdf-generator/dist ./pdf-generator/dist

EXPOSE ${PORT}

CMD ["sh", "-c", "gunicorn --workers ${WORKERS} --threads ${THREADS} --preload --bind 0.0.0.0:${PORT} encrypt_service:app"]
