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
├── pdf-generator/
│   ├── dist/                    # Built PDF visualizer (ksef-fe-invoice-converter.js)
│   └── i18n/en.json             # Maintained EN translation, reapplied on every rebuild
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
├── docker/                      # Everything Docker-related
│   ├── Dockerfile
│   ├── Dockerfile.dockerignore  # Build-context excludes (paths relative to repo root)
│   ├── docker-compose.yml       # Base compose config
│   ├── docker-compose.dev.yml   # Dev override (port 5001)
│   ├── docker-compose.prod.yml  # Prod override (port 5000)
│   ├── docker-compose.ssl.yml   # Optional TLS proxy overlay (port 443)
│   ├── build-image.sh           # Build and export Docker image as tar
│   ├── certs/                   # Generated TLS material (not committed)
│   └── proxy/                   # nginx TLS-termination image
│       ├── Dockerfile
│       ├── entrypoint.sh        # Reuse-or-generate certificate provisioning
│       └── nginx.conf.template
└── setup-ssl.sh                 # Nginx + Let's Encrypt (Docker or systemd)

```

## Rebuilding the PDF Generator

`pdf-generator/dist/` is a build of [CIRFMF/ksef-pdf-generator](https://github.com/CIRFMF/ksef-pdf-generator),
vendored so the service needs no Node toolchain at runtime. The source clone is **not** part
of this repository.

**Upstream ships `src/lib-public/i18n/lang/en.json` filled with `ExampleText` placeholders** —
there is no official English wording for KSeF field labels. This project maintains its own
translation in `pdf-generator/i18n/en.json`, reviewed and corrected by a consultant. Building
from a clean upstream checkout without reapplying it produces PDFs whose every English label
reads `ExampleText`, and nothing fails loudly when that happens.

```bash
git clone https://github.com/CIRFMF/ksef-pdf-generator
cd ksef-pdf-generator && git checkout <tag>

# Reapply the maintained EN translation — do not skip this.
cp ../pdf-generator/i18n/en.json src/lib-public/i18n/lang/en.json

npm ci && npm run build
cp -r dist ../pdf-generator/dist
```

Verify before committing the result:

```bash
# Must print 0. Anything else means the translation was not applied.
grep -c ExampleText pdf-generator/dist/ksef-fe-invoice-converter.js
```

If upstream adds translation keys, reconcile them into `pdf-generator/i18n/en.json` rather
than taking the upstream file: a key missing from our file makes i18next fall back to
printing the key itself. Upstream `pl.json` is the authoritative key set — it is a strict
superset of `en.json`, whose key names also carry typos (`taxInclusiveAmount ` with a
trailing space, `registration.Identifier` capitalised). List what needs translating with:

```bash
python3 - <<'EOF'
import json
def flat(o, p=''):
    for k, v in o.items():
        n = f'{p}.{k}' if p else k
        yield from flat(v, n) if isinstance(v, dict) else [(n, v)]
ours = dict(flat(json.load(open('pdf-generator/i18n/en.json'))))
theirs = dict(flat(json.load(open('ksef-pdf-generator/src/lib-public/i18n/lang/pl.json'))))
for k in sorted(set(theirs) - set(ours)):
    print(k, '|', theirs[k])
EOF
```

## Cryptographic Specifications

| Operation | Algorithm |
|---|---|
| RSA encryption (`/encrypt`) | RSAES-OAEP, MGF1 + SHA-256 |
| XML signing (`/sign_xml`) | XAdES enveloped, RSA-SHA256 or ECDSA-SHA256 (P-256) |
| Link signing (`/sign_link`) | RSA-PSS or ECDSA P-256, Base64URL output |
| Tunnel key wrapping (`/consume`) | CMS EnvelopedData (RFC 5652), RSAES-PKCS1-v1_5 [^cms] |
| Tunnel payload (`/consume`) | AES-256-CBC, PKCS7 padding |
| Internal keypairs (`/get_pub_cert`) | RSA-2048, self-signed X.509, TTL-based expiry |

[^cms]: `cms_encrypt_with_cert` shells out to `openssl cms -encrypt` without
`-keyopt rsa_padding_mode:oaep`, so the key transport algorithm in the envelope is
OpenSSL's default `rsaEncryption` (RSAES-PKCS1-v1_5), not OAEP. `/encrypt` is a separate
path and does use RSAES-OAEP. Changing the CMS padding would break compatibility with
existing SAP clients, so it is a deliberate interop constraint rather than an oversight.

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
