# 🔐 KSeF RSA Encryptor API

REST API do szyfrowania danych (np. kluczy AES lub tokenów) zgodnie z wymaganiami **KSeF**,  
z wykorzystaniem algorytmu **RSAES-OAEP (MGF1 + SHA-256)**.

Serwis jest zbudowany w oparciu o **Flask + Gunicorn**, udostępnia dokumentację przez **Swagger UI**,  
wspiera pełny **CORS** (dla bezpośrednich testów z przeglądarki) oraz zawiera dodatkowe endpointy do podpisów
(`/sign_xml`, `/sign_link`) wykorzystywanych w kontekście KSeF (XAdES oraz QR/KOD II).

---

- [Features](#features)
- [Endpoints](#endpoints)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Local Run](#local-run)
- [Example API Usage](#example-api-usage)
- [Run as a Linux Service (systemd)](#run-as-a-linux-service-systemd)
- [Run as a Linux Service (systemd) — Gunicorn Variant](#run-as-a-linux-service-systemd--gunicorn-variant)
- [Run in Docker](#run-in-docker)
- [Health-check (for K8s / monitoring)](#health-check-for-k8s--monitoring)
- [OpenAPI Definition](#openapi-definition)
- [Manual Tests](#manual-tests)
- [Dependencies](#dependencies)
- [📜 CHANGELOG](#-changelog)
- [Author](#author)
- [📄 License](#-license)

---

## Features

- Szyfrowanie RSAES-OAEP (MGF1 + SHA-256)
- Podpisywanie XML w XAdES (endpoint `/sign_xml`) z wyborem algorytmu (RSA-SHA256 / ECDSA-SHA256)
- Podpisywanie linku weryfikacyjnego QR / KOD II (endpoint `/sign_link`) z wyborem algorytmu:
  - RSA-PSS (MGF1-SHA256, salt=32)
  - ECDSA P-256 / SHA-256 (format podpisu: P1363 lub DER)
- Dokumentacja OpenAPI (Swagger UI)
- Endpoint health-check (`/health`)
- Gotowe uruchomienie w Dockerze z Gunicorn
- CORS – działa zarówno w Swagger UI, jak i z frontendów JS
- Definicja API w pliku `swaggerapi.yaml`

---

## Endpoints

### `/encrypt`

Szyfruje dane wejściowe RSAES-OAEP (MGF1 + SHA-256).  
Wejście/wyjście w JSON, dane binarne przekazywane w Base64.

### `/sign_xml`

Podpisuje przekazany XML w formacie XAdES (enveloped).  
Wejście: `xml_b64`, `cert_pem_b64`, `key_pem_b64` (+ opcjonalnie `key_password_b64`) oraz `alg`.  
Wyjście: `signed_xml_b64` oraz `alg_used`.

### `/sign_link`

Podpisuje link weryfikacyjny (QR/KOD II) zgodnie z wymaganiami KSeF.  
Wejście: `link_b64`, `cert_pem_b64`, `key_pem_b64` (+ opcjonalnie `key_password_b64`) oraz `alg` i (dla ECDSA) `ecdsa_format`.  
Wyjście: `link_b64` (Base64 kompletnego URL) oraz `alg_used` / `ecdsa_format_used`.

### `/health`

Zwraca status działania serwisu.

---

## Project Structure

```
.
├── encrypt_service.py      # Główna aplikacja Flask
├── swaggerapi.yaml         # Definicja API (OpenAPI / Swagger)
├── requirements.txt        # Zależności Pythona
└── Dockerfile              # Kontener Docker (Python + Gunicorn)
```

---

## Requirements

- Python **3.10+**
- Pip / venv
- Docker (opcjonalnie)

---

## Local Run

### Klonowanie repozytorium
```bash
git clone https://github.com/zvgelo/KSeF-RSA-Encryptor-API.git
cd KSeF-RSA-Encryptor-API
```

### Instalacja zależności
```bash
python -m venv venv
source venv/bin/activate  # Linux / macOS
venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### Uruchomienie serwisu
```bash
python encrypt_service.py
```

Serwis będzie dostępny pod adresem:  
http://localhost:5000

Swagger UI:  
http://localhost:5000/apidocs

---

## Example API Usage

### Endpoint `/encrypt`

**POST** `http://localhost:5000/encrypt`

#### Przykładowe żądanie:
```json
{
  "data_b64": "ZGFuZV9pbnB1dA==",
  "cert_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...",
  "return_b64": true
}
```

#### Przykładowa odpowiedź:
```json
{
  "status": "ok",
  "encrypted_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."
}
```

### Endpoint `/health`

**GET** `http://localhost:5000/health`

#### Przykładowa odpowiedź:
```json
{
  "status": "ok",
  "service": "KSeF RSA Encryptor"
}
```

---

## Run as a Linux Service (systemd)

Ten przykład pokazuje, jak uruchomić **KSeF RSA Encryptor API** jako usługę systemd na Linuxie.  
Usługa uruchamia się automatycznie po restarcie systemu i loguje wyjście do `/var/log`.

---

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

Rekomendowane dla **środowisk produkcyjnych** — wspiera wielu workerów i wątki.  
Gunicorn zarządza procesami workerów, co zwykle poprawia stabilność i wydajność.

---

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

Definicja jest dostępna w pliku `swaggerapi.yaml`.  
Możesz ją też pobrać jako JSON:

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
Open: http://localhost:5000/apidocs

---

## Dependencies

| Package | Description |
|----------|-------------|
| **Flask** | Lekki framework webowy |
| **Flasgger** | Swagger UI dla Flask |
| **Flask-CORS** | Obsługa CORS |
| **Cryptography** | Biblioteka kryptograficzna |
| **Gunicorn** | Produkcyjny serwer WSGI |
| **lxml** | Parser XML (wymagany do podpisu) |
| **signxml** | Implementacja podpisów XML/XAdES |

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
...
---

## Author

**Grzegorz Szawuła**

---

## 📄 License

Ten projekt jest udostępniany na licencji **MIT**.  
Korzystaj zgodnie z politykami bezpieczeństwa obowiązującymi w Twojej organizacji.
