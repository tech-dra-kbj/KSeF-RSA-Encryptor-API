# Architecture

## Overview

```
Client App / ERP
      │
      ▼ REST
Flask API Gateway (encrypt_service.py)
      │
      ├── routes/legacy_encrypt.py   → /encrypt
      ├── routes/sign_xml.py         → /sign_xml
      ├── routes/sign_link.py        → /sign_link
      ├── routes/pdf.py              → /generatePDF
      ├── routes/internal_keys.py    → /get_pub_cert
      ├── routes/consume.py          → /consume
      └── routes/misc.py             → / /health
              │
              ├── core/key_manager.py      ← SQLite (instance/keys.db, WAL)
              ├── core/crypto_utils.py     ← RSA, AES-CBC, CMS, X.509
              ├── core/consume_service.py  ← decrypt → dispatch → encrypt
              └── core/pdf_service.py      ← subprocess Node.js bridge
```

## Project Structure

```
.
├── encrypt_service.py           # App factory, blueprint registration
├── swaggerapi.yaml              # OpenAPI definition
├── pdf_generator_bridge.mjs     # Node.js ESM bridge for PDF generation
├── pdf-generator/dist/          # Built PDF visualizer (ksef-fe-invoice-converter.js)
├── core/
│   ├── config.py                # Environment variable defaults
│   ├── database.py              # SQLite connection + WAL init
│   ├── key_manager.py           # RSA keypair lifecycle (generate, reuse, expire)
│   ├── crypto_utils.py          # CMS, AES-CBC, X.509 helpers
│   ├── consume_service.py       # Secure tunnel: decrypt → dispatch → encrypt
│   └── pdf_service.py           # Node.js subprocess wrapper
├── routes/
│   ├── misc.py                  # GET / and GET /health
│   ├── legacy_encrypt.py        # POST /encrypt
│   ├── sign_xml.py              # POST /sign_xml
│   ├── sign_link.py             # POST /sign_link
│   ├── pdf.py                   # POST /generatePDF
│   ├── internal_keys.py         # POST /get_pub_cert
│   └── consume.py               # POST /consume
├── tests/                       # pytest test suite
├── Dockerfile
├── docker-compose.yml           # Base compose config
├── docker-compose.dev.yml       # Dev override (port 5001)
├── docker-compose.prod.yml      # Prod override (port 5000)
└── build-image.sh               # Build and export Docker image as tar

```

## Cryptographic Specifications

| Operation | Algorithm |
|---|---|
| RSA encryption (`/encrypt`) | RSAES-OAEP, MGF1 + SHA-256 |
| XML signing (`/sign_xml`) | XAdES enveloped, RSA-SHA256 or ECDSA-SHA256 (P-256) |
| Link signing (`/sign_link`) | RSA-PSS or ECDSA P-256, Base64URL output |
| Tunnel key wrapping (`/consume`) | CMS EnvelopedData (RFC 5652), RSA-OAEP |
| Tunnel payload (`/consume`) | AES-256-CBC, PKCS7 padding |
| Internal keypairs (`/get_pub_cert`) | RSA-2048, self-signed X.509, TTL-based expiry |

## Secure Tunnel Flow (`/consume`)

```
Client                              API
  │                                  │
  │── GET /get_pub_cert (sid) ──────▶│ generates RSA keypair, stores in SQLite
  │◀─ cert_pem_b64, kid ────────────│
  │                                  │
  │  Client wraps inner request:     │
  │  [JSON payload]                  │
  │    → AES-256-CBC (random key+IV) │
  │    → AES key wrapped in CMS      │
  │       using server's certificate │
  │                                  │
  │── POST /consume ────────────────▶│ decrypts CMS → AES key
  │   enc_key_b64, iv_b64,          │ decrypts payload → JSON
  │   ciphertext_b64                 │ dispatches to local endpoint
  │   [reply_cert_pem_b64 optional] │ encrypts response (if reply_cert)
  │◀─ plaintext_b64 or reply ───────│
```
