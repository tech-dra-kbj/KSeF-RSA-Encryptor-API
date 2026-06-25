# Deployment

## Local (development)

```bash
git clone https://github.com/tech-dra-kbj/KSeF-RSA-Encryptor-API.git
cd KSeF-RSA-Encryptor-API

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python encrypt_service.py
```

Service: `http://localhost:5000`  
Swagger UI: `http://localhost:5000/apidocs`

Node.js 20+ must be installed and `pdf-generator/dist/` must contain the visualizer bundle.

---

## Gunicorn (production)

```bash
gunicorn --workers 3 --threads 2 --bind 0.0.0.0:5000 encrypt_service:app
```

---

## systemd

```bash
sudo nano /etc/systemd/system/ksef-encryptor.service
```

```ini
[Unit]
Description=KSeF Integration API
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/KSeF-RSA-Encryptor-API

# Required if Node.js is installed via nvm
Environment="KSEF_NODE_BIN=/home/ubuntu/.nvm/versions/node/v20.20.2/bin/node"
Environment="PATH=/home/ubuntu/.nvm/versions/node/v20.20.2/bin:/usr/local/bin:/usr/bin:/bin"

Environment="PORT=5000"
Environment="WORKERS=3"
Environment="THREADS=2"
ExecStart=/home/ubuntu/KSeF-RSA-Encryptor-API/.venv/bin/gunicorn --workers ${WORKERS} --threads ${THREADS} --bind 0.0.0.0:${PORT} encrypt_service:app
Restart=always
RestartSec=5
StandardOutput=append:/var/log/encrypt_service.log
StandardError=append:/var/log/encrypt_service.err

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ksef-encryptor.service
sudo systemctl start ksef-encryptor.service
sudo systemctl status ksef-encryptor.service
```

---

## Docker Compose

The recommended setup runs **two services simultaneously** on the same machine:

| Service | Port | Image tag | Workers |
|---|---|---|---|
| Production | `5000` | `ksef-integration-api:stable` | 3 |
| Development | `5001` | `ksef-integration-api:latest` | 2 |

Use `-p` (project name) so each stack gets its own network and container namespace and they do not overwrite each other.

### Start both services

```bash
# Production
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d

# Development
docker compose -p ksef-dev -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Verify both are running:
```bash
docker ps --filter name=ksef
```

Expected:
```
ksef-encryptor      ksef-integration-api:stable   0.0.0.0:5000->5000/tcp
ksef-encryptor-dev  ksef-integration-api:latest   0.0.0.0:5001->5000/tcp
```

### Build images before starting

```bash
# Stable image for prod
docker build -t ksef-integration-api:stable .

# Latest image for dev (or use --build flag)
docker build -t ksef-integration-api:latest .
```

Or let compose build on the fly with `--build`:
```bash
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -p ksef-dev  -f docker-compose.yml -f docker-compose.dev.yml  up -d --build
```

### Stop

```bash
docker compose -p ksef-prod down
docker compose -p ksef-dev down
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Internal container port |
| `WORKERS` | `3` | Gunicorn worker processes |
| `THREADS` | `2` | Threads per worker |
| `KEY_DB_PATH` | `instance/keys.db` | SQLite key database path |
| `KEY_TTL_SECONDS` | `86400` | Key TTL in seconds (24h) |
| `KSEF_NODE_BIN` | `node` | Path to Node.js binary |
| `KSEF_PDF_BRIDGE_PATH` | `./pdf_generator_bridge.mjs` | Node.js PDF bridge path |
| `KSEF_PDF_MODULE_PATH` | `./pdf-generator/dist/ksef-fe-invoice-converter.js` | PDF generator module path |
| `KSEF_PDF_TIMEOUT_SECONDS` | `60` | PDF generation timeout (seconds) |

---

## Docker — offline deployment (no repo access)

Build and export image as a tar archive:

```bash
# produces ksef-integration-api_stable.tar
./build-image.sh stable
```

Transfer to target machine and load:

```bash
docker load -i ksef-integration-api_stable.tar
docker compose -p ksef-prod -f docker-compose.yml -f docker-compose.prod.yml up -d
```

