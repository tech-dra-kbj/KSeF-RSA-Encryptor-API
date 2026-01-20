# 🔐 KSeF RSA Encryptor API

REST API do operacji kryptograficznych wykorzystywanych w integracji z **KSeF**, w szczególności:
- szyfrowanie danych **RSAES-OAEP (MGF1 + SHA-256)**,
- podpisywanie linku weryfikacyjnego **KOD II** (offline) algorytmami **RSA-PSS** lub **ECDSA P-256**,
- podpis XML w formacie **XAdES (enveloped)** dla żądań uwierzytelniania.

Serwis jest zbudowany w oparciu o **Flask + Gunicorn**, udostępnia dokumentację przez **Swagger UI** oraz ma włączony **CORS** (ułatwia testy z przeglądarki).

---

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Local Run](#local-run)
- [API Overview](#api-overview)
  - [`/encrypt`](#encrypt)
  - [`/sign_link`](#sign_link)
  - [`/sign_xml`](#sign_xml)
  - [`/health`](#health)
- [Manual Tests (curl)](#manual-tests-curl)
  - [Base64 helpers (Linux/macOS)](#base64-helpers-linuxmacos)
  - [Test `/sign_link` (ECDSA)](#test-sign_link-ecdsa)
  - [Test `/sign_xml` (XAdES)](#test-sign_xml-xades)
  - [Save signed XML to file](#save-signed-xml-to-file)
- [Security Notes](#security-notes)
- [OpenAPI / Swagger](#openapi--swagger)
- [Changelog](#changelog)
- [Dependencies](#dependencies)
- [Author](#author)
- [License](#license)

---

## Features

- **/encrypt** – RSAES-OAEP (MGF1 + SHA-256)
- **/sign_link** – podpis linku KOD II (offline):  
  - `rsa_pss` (RSASSA-PSS, SHA-256, MGF1(SHA-256), salt=32)  
  - `ecdsa_p256` (ECDSA P-256 / SHA-256), format podpisu: `p1363` lub `der`
- **/sign_xml** – podpis XML w formacie **XAdES (enveloped)**:  
  - `rsa_sha256` lub `ecdsa_sha256` (dla EC wymuszane P-256)
- Swagger UI (`/apidocs`)
- Health-check (`/health`)
- Docker-ready + Gunicorn
- CORS enabled

---

## Project Structure

```
.
├── encrypt_service.py      # Main Flask app (endpointy: /encrypt, /sign_link, /sign_xml)
├── swaggerapi.yaml         # Swagger / OpenAPI definition (Flasgger template)
├── requirements.txt        # Python dependencies
└── Dockerfile              # Docker container definition (Python + Gunicorn)
```

---

## Requirements

- Python **3.10+** (rekomendowane)
- pip / venv
- Docker (opcjonalnie)

> Uwaga: endpointy podpisu XML wymagają bibliotek XML/XAdES (`lxml`, `signxml`). Jeżeli w requirements ich nie masz — dodaj je jawnie (szczegóły w sekcji [Dependencies](#dependencies)).

---

## Local Run

### Clone repository
```bash
git clone https://github.com/zvgelo/KSeF-RSA-Encryptor-API.git
cd KSeF-RSA-Encryptor-API
```

### Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### Run the service
```bash
python encrypt_service.py
```

Service:
- http://localhost:5000  
Swagger UI:
- http://localhost:5000/apidocs

---

## API Overview

Definicja endpointów i schematów jest w `swaggerapi.yaml` i jest ładowana przez Flasgger.

### <a id="encrypt"></a>`/encrypt`

**POST** `/encrypt`

Szyfruje `data_b64` kluczem publicznym z certyfikatu `cert_b64` (PEM/DER w Base64).

**Request JSON:**
```json
{
  "data_b64": "ZGFuZV9pbnB1dA==",
  "cert_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
  "return_b64": true
}
```

**Response JSON:**
```json
{
  "status": "ok",
  "encrypted_b64": "..."
}
```

---

### <a id="sign_link"></a>`/sign_link`

**POST** `/sign_link`

Podpisuje link weryfikacyjny KOD II (offline).

- Wejściowy link może być:
  - pełnym URL `https://...` lub
  - bez schematu `qr-demo.ksef.mf.gov.pl/...`
- Podpisywany jest ciąg: `host/path` **bez** `https://` i **bez** końcowego `/`.
- Certyfikat jest wykorzystywany do walidacji dopasowania do klucza prywatnego (public key match).
- Hasło do klucza przekazuj jako **Base64** w polu `key_password_b64`.

**Request JSON (ECDSA P-256, format P1363):**
```json
{
  "link_b64": "cXItZGVtby5rc2VmLm1mLmdvdi5wbC9jZXJ0aWZpY2F0ZS9OaXAvLi4u",
  "cert_pem_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
  "key_pem_b64": "LS0tLS1CRUdJTiBFTkNSWVBURUQgUFJJVkFURSBLRVktLS0tLQ==",
  "key_password_b64": "emFxMUBXU1hjZGUzJFJGVg==",
  "alg": "ecdsa_p256",
  "ecdsa_format": "p1363"
}
```

**Response JSON:**
```json
{
  "link_b64": "aHR0cHM6Ly9xci1kZW1vLmtzZWYubWYuZ292LnBsL2NlcnRpZmljYXRlL...==",
  "alg_used": "ecdsa_p256",
  "ecdsa_format_used": "p1363"
}
```

---

### <a id="sign_xml"></a>`/sign_xml`

**POST** `/sign_xml`

Podpisuje XML w formacie **XAdES (enveloped)**. Wejścia/wyjścia są w Base64.

- `alg`:
  - `rsa_sha256` – gdy klucz prywatny RSA
  - `ecdsa_sha256` – gdy klucz prywatny EC (wymuszane P-256)

**Request JSON:**
```json
{
  "xml_b64": "PEF1dGhUb2tlblJlcXVlc3Q+Li4uPC9BdXRoVG9rZW5SZXF1ZXN0Pg==",
  "cert_pem_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
  "key_pem_b64": "LS0tLS1CRUdJTiBFTkNSWVBURUQgUFJJVkFURSBLRVktLS0tLQ==",
  "key_password_b64": "emFxMUBXU1hjZGUzJFJGVg==",
  "alg": "ecdsa_sha256"
}
```

**Response JSON:**
```json
{
  "signed_xml_b64": "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4K...",
  "alg_used": "ecdsa_sha256"
}
```

---

### <a id="health"></a>`/health`

**GET** `/health`

**Response JSON:**
```json
{
  "status": "ok",
  "service": "KSeF RSA Encryptor"
}
```

---

## Manual Tests (curl)

### Base64 helpers (Linux/macOS)

**Linux:**
```bash
b64_file() { base64 -w0 "$1"; }
```

**macOS:**
```bash
b64_file() { base64 < "$1" | tr -d '\n'; }
```

Dla haseł:
```bash
b64_str() { printf '%s' "$1" | base64 | tr -d '\n'; }
```

---

### Test `/sign_link` (ECDSA)

Przykładowy link (bez `https://` też działa):
```
qr-demo.ksef.mf.gov.pl/certificate/Nip/8111693370/8111693370/013C34D4C9B7E276/EcbwwuZ5hE_7BLZ4dse-jJK0wlLMNWl5IVTuXtCrHNk
```

Zakładamy pliki:
- cert: `cert-offline-demo-811.crt`
- key:  `cert-offline-demo-811.key`
- pass: `zaq1@WSXcde3$RFV`

```bash
LINK='qr-demo.ksef.mf.gov.pl/certificate/Nip/8111693370/8111693370/013C34D4C9B7E276/EcbwwuZ5hE_7BLZ4dse-jJK0wlLMNWl5IVTuXtCrHNk'

LINK_B64="$(printf '%s' "$LINK" | base64 | tr -d '\n')"
CERT_B64="$(base64 < cert-offline-demo-811.crt | tr -d '\n')"
KEY_B64="$(base64 < cert-offline-demo-811.key | tr -d '\n')"
PASS_B64="$(printf '%s' 'zaq1@WSXcde3$RFV' | base64 | tr -d '\n')"

curl -s http://localhost:5000/sign_link \
  -H "Content-Type: application/json" \
  -d "{\"link_b64\":\"${LINK_B64}\",\"cert_pem_b64\":\"${CERT_B64}\",\"key_pem_b64\":\"${KEY_B64}\",\"key_password_b64\":\"${PASS_B64}\",\"alg\":\"ecdsa_p256\",\"ecdsa_format\":\"p1363\"}" \
| jq .
```

Aby podejrzeć wynik jako tekst (URL):
```bash
curl -s http://localhost:5000/sign_link \
  -H "Content-Type: application/json" \
  -d "{\"link_b64\":\"${LINK_B64}\",\"cert_pem_b64\":\"${CERT_B64}\",\"key_pem_b64\":\"${KEY_B64}\",\"key_password_b64\":\"${PASS_B64}\",\"alg\":\"ecdsa_p256\",\"ecdsa_format\":\"p1363\"}" \
| jq -r '.link_b64' | base64 -d
echo
```

---

### Test `/sign_xml` (XAdES)

Pliki:
- cert: `Auth-811-test.crt`
- key:  `Auth-811-test.key`
- pass: `zaq1@WSXcde3$RFV`
- xml:  `request.xml`

```bash
XML_B64="$(base64 < request.xml | tr -d '\n')"
CERT_B64="$(base64 < Auth-811-test.crt | tr -d '\n')"
KEY_B64="$(base64 < Auth-811-test.key | tr -d '\n')"
PASS_B64="$(printf '%s' 'zaq1@WSXcde3$RFV' | base64 | tr -d '\n')"

# Uwaga: dobierz alg zgodnie z typem klucza:
# - rsa_sha256 dla RSA
# - ecdsa_sha256 dla EC (P-256)
curl -s http://localhost:5000/sign_xml \
  -H "Content-Type: application/json" \
  -d "{\"xml_b64\":\"${XML_B64}\",\"cert_pem_b64\":\"${CERT_B64}\",\"key_pem_b64\":\"${KEY_B64}\",\"key_password_b64\":\"${PASS_B64}\",\"alg\":\"ecdsa_sha256\"}" \
| jq .
```

---

### Save signed XML to file

```bash
curl -s http://localhost:5000/sign_xml \
  -H "Content-Type: application/json" \
  -d "{\"xml_b64\":\"${XML_B64}\",\"cert_pem_b64\":\"${CERT_B64}\",\"key_pem_b64\":\"${KEY_B64}\",\"key_password_b64\":\"${PASS_B64}\",\"alg\":\"ecdsa_sha256\"}" \
| jq -r '.signed_xml_b64' | base64 -d > signed_request.xml

echo "Saved: signed_request.xml"
```

---

## Security Notes

- Serwis przyjmuje klucze prywatne i hasła — uruchamiaj go w zaufanym środowisku (sieć wewnętrzna, VPN, reverse proxy, ACL).
- Rozważ ograniczenie rozmiaru payloadów oraz rate limiting.
- W produkcji używaj TLS (np. Nginx/ALB) oraz wyłącz debug.
- Nie loguj wejść zawierających klucze/hasła.

---

## OpenAPI / Swagger

- Swagger UI: `GET /apidocs`
- Spec (JSON): `GET /apispec_1.json`
- Źródło definicji: `swaggerapi.yaml`

---

## Changelog

# 📜 CHANGELOG
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
GitHub: [zvgelo](https://github.com/zvgelo)

---

## Dependencies

Minimalnie:
- Flask
- Flasgger
- Flask-CORS
- cryptography
- gunicorn

Dla endpointów podpisu (`/sign_xml`) wymagane są dodatkowo:
- `lxml`
- `signxml` (moduł XAdES / XMLDSig)

Jeżeli chcesz, dodaj je do `requirements.txt` (przykładowo):
- `lxml==5.*`
- `signxml==4.*` (lub wersja zgodna z Twoim środowiskiem)

---

## Author

**Grzegorz Szawuła**

---

## 📄 License

This project is licensed under the **MIT License**.
Use in accordance with your organization’s security policies.
