# KSeF Integration API

REST API supporting integration with KSeF (Krajowy System e-Faktur).

Built with **Flask + Gunicorn**. Provides cryptographic operations required by the KSeF gateway: RSA-OAEP encryption, XAdES XML signing, QR link signing, invoice PDF generation, and a secure CMS-based encrypted tunnel.

---

## Documentation

- [API Endpoints](docs/api.md)
- [Deployment](docs/deployment.md) — local, systemd, Docker
- [Operations](docs/operations.md) — first deployment, updates, rollback, logs
- [Architecture & Cryptography](docs/architecture.md)
- [FAQ](docs/faq.md)
- [CHANGELOG](CHANGELOG.md)

Interactive API docs (Swagger UI): `http://localhost:5000/apidocs`

---

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python encrypt_service.py
```

Or with Docker:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Features

- RSAES-OAEP encryption (MGF1 + SHA-256) for KSeF session tokens
- XAdES enveloped XML signing (RSA-SHA256 or ECDSA-SHA256)
- QR verification link signing (RSA-PSS or ECDSA P-256)
- Invoice PDF generation via Node.js bridge (`/generatePDF`)
- Secure CMS encrypted tunnel (`/consume`) with internal key management
- SQLite key store with TTL-based expiry (WAL mode)
- Swagger UI (`/apidocs`), CORS support, Docker-ready

---

## Requirements

- Python 3.10+
- Node.js 20+ (required for `/generatePDF`)

---

## Author

**KBJ DRA** — [github.com/tech-dra-kbj](https://github.com/tech-dra-kbj)

## License

MIT
