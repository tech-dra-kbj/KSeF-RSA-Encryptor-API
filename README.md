# 🔐 KSeF RSA Encryptor API

REST API for cryptographic operations compliant with **KSeF** requirements.

The service is built with **Flask + Gunicorn**, provides documentation via **Swagger UI**, and supports full **CORS** (for direct testing from browsers).

---

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Local Run](#local-run)
- [Endpoints](#endpoints)
  - [`/encrypt`](#encrypt)
  - [`/sign_xml`](#sign_xml)
  - [`/sign_link`](#sign_link)
  - [`/health`](#health)
- [Example API Usage](#example-api-usage)
- [Run as a Linux Service (systemd)](#run-as-a-linux-service-systemd)
- [Run as a Linux Service (systemd) — Gunicorn Variant](#run-as-a-linux-service-systemd--gunicorn-variant)
- [Run in Docker](#run-in-docker)
- [OpenAPI Definition](#openapi-definition)
- [Manual Tests](#manual-tests)
- [Dependencies](#dependencies)
- [Changelog](#-changelog)
- [Author](#author)
- [License](#-license)

---

## Features

- RSAES-OAEP encryption (MGF1 + SHA-256) for KSeF RSA encryption use-cases
- XAdES signing for XML payloads (RSA-SHA256 or ECDSA-SHA256, enveloped)
- KSeF offline QR verification link signing (RSA-PSS or ECDSA P-256, Base64URL output)
- OpenAPI (Swagger UI) documentation
- Health-check endpoint (`/health`)
- Docker-ready with Gunicorn
- CORS support – works in Swagger UI and JS frontends
- External API definition in `swaggerapi.yaml`

---

## Project Structure

```text
.
├── encrypt_service.py      # Main Flask app
├── swaggerapi.yaml         # API definition (OpenAPI / Swagger)
├── requirements.txt        # Python dependencies
└── Dockerfile              # Docker container definition (Python + Gunicorn)
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
- http://localhost:5000

Swagger UI:
- http://localhost:5000/apidocs

---

## Endpoints

### `/encrypt`

Encrypts input bytes using **RSAES-OAEP (MGF1 + SHA-256)** with the public key extracted from a KSeF certificate.

Input and output are Base64 strings.

### `/sign_xml`

Signs an XML payload using **XAdES** in *enveloped* mode.

- Input: `xml_b64`, `cert_pem_b64`, `key_pem_b64`
- Optional: `key_password_b64`
- Algorithm selection: `alg` = `rsa_sha256` (default) or `ecdsa_sha256`
- Output: `signed_xml_b64` and `alg_used`

### `/sign_link`

Signs a KSeF offline verification link.

- Input: `link_b64`, `cert_pem_b64`, `key_pem_b64`
- Optional: `key_password_b64`
- Algorithm selection: `alg` = `rsa_pss` (default) or `ecdsa_p256`
- For ECDSA output format: `ecdsa_format` = `p1363` (default, R||S 32+32) or `der`
- Output: `link_b64`, `alg_used`, and optionally `ecdsa_format_used`

### `/health`

Simple health-check endpoint for monitoring/Kubernetes probes.

---

## Example API Usage

### Endpoint `/encrypt`

**POST** `http://localhost:5000/encrypt`

#### Example request
```json
{
  "data_b64": "ZGFuZV9pbnB1dA==",
  "cert_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...",
  "return_b64": true
}
```

#### Example response
```json
{
  "status": "ok",
  "encrypted_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."
}
```

### Endpoint `/sign_xml`

**POST** `http://localhost:5000/sign_xml`

#### Example request (RSA)
```json
{
  "xml_b64": "PEF1dGhUb2tlblJlcXVlc3Q+Li4uPC9BdXRoVG9rZW5SZXF1ZXN0Pg==",
  "cert_pem_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
  "key_pem_b64": "LS0tLS1CRUdJTiBFTkNSWVBURUQgUFJJVkFURSBLRVktLS0tLQ==",
  "key_password_b64": "emFxMUBXU1hjZGUzJFJGVg==",
  "alg": "rsa_sha256"
}
```

#### Example response
```json
{
  "signed_xml_b64": "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4...",
  "alg_used": "rsa_sha256"
}
```

### Endpoint `/sign_link`

**POST** `http://localhost:5000/sign_link`

#### Example request (ECDSA P-256, P1363 output)
```json
{
  "link_b64": "cXItZGVtby5rc2VmLm1mLmdvdi5wbC9jZXJ0aWZpY2F0ZS9OaXAvODExMTY5MzM3MC84MTExNjkzMzcwLzAxM0MzNEQ0QzlCN0UyNzYvRWNid3d1WjVoRV83QkxaNGRzZS1qSkswd2xMTU5XbDVJVlR1WHRDckhOaw==",
  "cert_pem_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
  "key_pem_b64": "LS0tLS1CRUdJTiBFTkNSWVBURUQgUFJJVkFURSBLRVktLS0tLQ==",
  "key_password_b64": "emFxMUBXU1hjZGUzJFJGVg==",
  "alg": "ecdsa_p256",
  "ecdsa_format": "p1363"
}
```

#### Example response
```json
{
  "link_b64": "aHR0cHM6Ly9xci1kZW1vLmtzZWYubWYuZ292LnBsL2NlcnRpZmljYXRlL05pcC84MTExNjkzMzcwLzgxMTE2OTMzNzAvMDEzQzM0RDRDOUI3RTI3Ni9FY2J3d3VaNWhFXzdCTFo0ZHNlLWpKSzB3bExNTldsNUlWVHNYdENySE5rL1RIRV9TSUdOQVRVUkU=",
  "alg_used": "ecdsa_p256",
  "ecdsa_format_used": "p1363"
}
```

---

## Run as a Linux Service (systemd)

This example shows how to run the **KSeF RSA Encryptor API** as a systemd service on Linux.  
The service starts automatically after a reboot and logs output to `/var/log`.

### Create a systemd unit file

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

## Run as a Linux Service (systemd) — Gunicorn Variant

Recommended for **production environments** — supports multiple workers and threads.  
Gunicorn manages worker processes automatically for improved stability.

### Create a systemd unit file

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

### Reload and start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable ksef-encryptor.service
sudo systemctl start ksef-encryptor.service
```

### Check status
```bash
sudo systemctl status ksef-encryptor.service
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

## OpenAPI Definition

Available in `swaggerapi.yaml`.  
You can also export it as JSON:

```bash
curl http://localhost:5000/apispec_1.json -o openapi.json
```

---

## Manual Tests

### Using `curl` (`/encrypt`)
```bash
curl -X POST http://localhost:5000/encrypt   -H "Content-Type: application/json"   -d '{"data_b64":"ZGFuZQ==","cert_b64":"MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."}'
```

### In Swagger UI
Open:
- http://localhost:5000/apidocs

---

## Dependencies

| Package | Description |
|--------|-------------|
| **Flask** | Lightweight web framework |
| **Flasgger** | Swagger UI for Flask |
| **Flask-CORS** | CORS support |
| **Cryptography** | Cryptographic library |
| **Gunicorn** | Production-grade WSGI server |
| **lxml** | XML parsing |
| **signxml** | XMLDSig/XAdES signing support |

---

## 📜 CHANGELOG
**KSeF RSA Encryptor API**

_Automatically compiled from Git commit history._

---

## [1.0.3] – 2025-10-17
### Changed
- Disabled **pretty print** in JSON responses to improve integration with external systems.
- Adjusted JSON output formatting (compact mode) for cleaner API responses.

---

## [1.0.2] – 2025-10-17
### Fixed
- Improved error handling and response consistency for `/encrypt` endpoint.

---

## [1.0.1] – 2025-10-16
### Added
- Added **Swagger / OpenAPI** documentation (`swaggerapi.yaml`).
- Added **project documentation** for external security audits (README, API specs, etc.).

---

## [1.0.0] – 2025-10-15
### Initial release
- Implemented core RSA encryption API:
  - `/encrypt` endpoint using RSAES-OAEP (MGF1 + SHA-256)
  - `/health` endpoint for monitoring
- Added input validation and structured JSON error codes.
- Added Flask app structure with CORS and Swagger integration.
- Added `Dockerfile` for containerized deployment.
- Initial repository setup and dependency list (`requirements.txt`).

---

### Author
**Grzegorz Szawuła**  
GitHub: https://github.com/zvgelo

---

## Author

**Grzegorz Szawuła**

---

## 📄 License

This project is licensed under the **MIT License**.  
Use it in accordance with your organization’s security policies.
