# 🔐 KSeF RSA Encryptor API

REST API for encrypting data (e.g., AES keys or tokens) in compliance with **KSeF** requirements,  
using the **RSAES-OAEP (MGF1 + SHA-256)** algorithm.

The service is built with **Flask + Gunicorn**, provides documentation via **Swagger UI**,  
and supports full **CORS** (for direct testing from browsers).

---

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Local Run](#local-run)
- [Example API Usage](#example-api-usage)
- [Run as Linux Service (systemd)](#run-as-linux-service-systemd)
- [Run as Linux Service (systemd) — Gunicorn Variant](#run-as-linux-service-systemd--gunicorn-variant)
- [Run in Docker](#run-in-docker)
- [Health-check (for K8s / monitoring)](#health-check-for-k8s--monitoring)
- [OpenAPI Definition](#openapi-definition)
- [Manual Tests](#manual-tests)
- [Dependencies](#dependencies)

---

## Features

- RSAES-OAEP encryption (MGF1 + SHA-256)
- OpenAPI (Swagger UI) documentation
- Health-check endpoint (`/health`)
- Docker-ready with Gunicorn
- CORS support – works in Swagger UI and JS frontends
- External API definition in `openapi.yaml`

---

## Project Structure

```
.
├── encrypt_service.py      # Main Flask app
├── openapi.yaml            # API definition (OpenAPI / Swagger)
├── requirements.txt        # Python dependencies
└── Dockerfile              # Docker container definition (Python 3.10 + Gunicorn)
```

---

## Requirements

- Python **3.10+**
- Pip / venv
- Docker (optional)

---

## Local Run

### Clone repository
```bash
git clone https://github.com/zvgelo/KSeF-RSA-Encryptor-API.git
cd KSeF-RSA-Encryptor-API
```

### Install dependencies
```bash
python -m venv venv
source venv/bin/activate  # Linux / macOS
venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### Run the service
```bash
python encrypt_service.py
```

Service will be available at:  
[http://localhost:5000](http://localhost:5000)

Swagger UI:  
[http://localhost:5000/apidocs](http://localhost:5000/apidocs)

---

## Example API Usage

### Endpoint `/encrypt`

**POST** `http://localhost:5000/encrypt`

#### Example request:
```json
{
  "data_b64": "ZGFuZV9pbnB1dA==",
  "cert_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...",
  "return_b64": true
}
```

#### Example response:
```json
{
  "status": "ok",
  "encrypted_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."
}
```

### Endpoint `/health`

**GET** `http://localhost:5000/health`

#### Example response:
```json
{
  "status": "ok",
  "service": "KSeF RSA Encryptor"
}
```

---

## Run as Linux Service (systemd)

This example shows how to run the **KSeF RSA Encryptor API** as a systemd service on Linux.  
The service starts automatically after a reboot and logs output to `/var/log`.

---

### Create systemd unit file

```bash
sudo nano /etc/systemd/system/ksef-encryptor.service
```

Example configuration (adjust paths and user):

```ini
[Unit]
Description=KSeF RSA Encryptor Flask Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/KSeF-RSA-Encryptor-API
Environment="PORT=5000"
ExecStart=/home/ubuntu/KSeF-RSA-Encryptor-API/.venv/bin/python3 /home/ubuntu/KSeF-RSA-Encryptor-API/encrypt_service.py
Restart=always
StandardOutput=append:/var/log/encrypt_service.log
StandardError=append:/var/log/encrypt_service.err

[Install]
WantedBy=multi-user.target
```

---

## Run as Linux Service (systemd) — Gunicorn Variant

Recommended for **production environments** — supports multiple workers and threads.  
Gunicorn manages worker processes automatically for improved stability.

---

### Create systemd unit file

```bash
sudo nano /etc/systemd/system/ksef-encryptor.service
```

Configuration (adjust paths and user):

```ini
[Unit]
Description=KSeF RSA Encryptor Gunicorn Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/KSeF-RSA-Encryptor-API
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

### Reload and start service
```bash
sudo systemctl daemon-reload
sudo systemctl enable ksef-encryptor.service
sudo systemctl start ksef-encryptor.service
```

### Check status
```bash
sudo systemctl status ksef-encryptor.service
```

Example:
```
● ksef-encryptor.service - KSeF RSA Encryptor Gunicorn Service
   Loaded: loaded (/etc/systemd/system/ksef-encryptor.service; enabled)
   Active: active (running) since Fri 2025-10-17 09:41:13 CEST; 10s ago
 Main PID: 21345 (gunicorn)
    Tasks: 4 (limit: 4915)
   CGroup: /system.slice/ksef-encryptor.service
           ├─21345 gunicorn master
           ├─21347 gunicorn: worker [1]
           ├─21348 gunicorn: worker [2]
           └─21349 gunicorn: worker [3]
```

---

## Run in Docker

### Build image
```bash
docker build -t ksef-encryptor .
```

### Run container
```bash
docker run -p 5000:5000 ksef-encryptor
```

### Custom port and Gunicorn workers
```bash
docker run -e PORT=8080 -e WORKERS=4 -e THREADS=2 -p 8080:8080 ksef-encryptor
```

---

## Health-check (for K8s / monitoring)

```bash
curl http://localhost:5000/health
```

Response:
```json
{ "status": "ok", "service": "KSeF RSA Encryptor" }
```

---

## OpenAPI Definition

Available in [`openapi.yaml`](./openapi.yaml).  
You can also export it as JSON:
```bash
curl http://localhost:5000/apispec_1.json -o openapi.json
```

---

## Manual Tests

### Using `curl`:
```bash
curl -X POST http://localhost:5000/encrypt   -H "Content-Type: application/json"   -d '{"data_b64": "ZGFuZQ==", "cert_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."}'
```

### In Swagger UI:
Open: [http://localhost:5000/apidocs](http://localhost:5000/apidocs)

---

## Dependencies

| Package | Description |
|----------|-------------|
| **Flask** | Lightweight web framework |
| **Flasgger** | Swagger UI for Flask |
| **Flask-CORS** | CORS support |
| **Cryptography** | Cryptographic library |
| **Gunicorn** | Production-grade WSGI server |

---

## Author

**Grzegorz Szawuła**

---

## 📄 License

This project is licensed under the **MIT License**.  
Use in accordance with your organization’s security policies.
