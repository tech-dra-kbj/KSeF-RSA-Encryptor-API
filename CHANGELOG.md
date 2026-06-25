# Changelog

All notable changes to the KSeF Integration API project will be documented in this file.

---

## [1.3.0] - 2026-06-25

### Added
- Added `/consume` endpoint — secure CMS encrypted RPC tunnel:
  - Accepts AES session key wrapped in CMS EnvelopedData and AES-256-CBC encrypted payload.
  - Dispatches decrypted inner request to a local endpoint (e.g. `/encrypt`).
  - Returns result as plaintext or re-encrypted with an optional client reply certificate.
- Added `/get_pub_cert` endpoint — internal RSA keypair and X.509 certificate provisioning per SID.
- Added internal key management (`core/key_manager.py`): RSA-2048 keypair generation, TTL-based expiry, automatic cleanup.
- Added SQLite database layer (`core/database.py`) with WAL mode for persistent key storage.
- Added Docker Compose dev/prod split (`docker-compose.dev.yml`, `docker-compose.prod.yml`).
- Added `build-image.sh` — builds and exports Docker image as a tar archive for offline deployment.
- Added `docs/` directory with split documentation: API reference, deployment, operations, architecture.

### Changed
- Refactored route structure into blueprints by responsibility (`routes/legacy_encrypt.py`, `routes/sign_xml.py`, `routes/sign_link.py`, `routes/pdf.py`, `routes/internal_keys.py`, `routes/consume.py`).
- Rebranded service to **KSeF Integration API**.
- Updated Swagger/OpenAPI definition to v1.3.0 with full English descriptions and new endpoints.

---

## [1.2.0] - 2026-04-01

### Added
- Added `/generatePDF` endpoint for generating invoice PDF visualizations from KSeF XML:
  - Supports FA(1), FA(2), FA(3), FA_RR invoice formats.
  - Input: `xml_b64` (Base64-encoded XML).
  - Response modes: `base64` (JSON with `pdf_b64`) or `binary` (`application/pdf`).
  - Optional `additional_data` passthrough to the PDF generator (`nrKSeF`, `qrCode`, `qr2Code`, `isMobile`).
  - Managed by [routes/pdf.py](routes/pdf.py) and [core/pdf_service.py](core/pdf_service.py).
- Added Node.js bridge [pdf_generator_bridge.mjs](pdf_generator_bridge.mjs) for PDF generation runtime.

### Changed
- Renamed input field from `xml_content` to `xml_b64` for consistency with other endpoints.
- Updated systemd service configuration to support Node.js installed via nvm (`KSEF_NODE_BIN` and `PATH` environment variables).
- Updated [swaggerapi.yaml](swaggerapi.yaml) with full `/generatePDF` schema including curl examples.

---

## [1.1.0] - 2026-01-19

### Added
- Added `/sign_link` endpoint for generating KSeF KOD II verification links with a cryptographic signature:
  - Supported algorithms:
    - RSA-PSS (SHA-256, MGF1(SHA-256), salt=32, minimum key size 2048)
    - ECDSA P-256 (SHA-256) with output formats:
      - IEEE P1363 (R||S, 64 bytes)
      - ASN.1 DER (RFC 3279)
  - Accepts links with or without `https://` scheme and normalizes trailing `/`.
  - Validates that certificate public key matches the provided private key.
  - Returns a ready-to-use link with signature appended as the last path segment.
  - Implemented in [routes/sign_link.py](routes/sign_link.py).
- Added `/sign_xml` endpoint for XAdES (enveloped) signing of XML payloads used in KSeF authentication flows.
  - Accepts input only as Base64 (`xml_b64`, `cert_pem_b64`, `key_pem_b64`).
  - Supports algorithm selection via `alg`: `rsa_sha256` or `ecdsa_sha256` (with P-256/secp256r1 curve enforcement).
  - Implemented in [routes/sign_xml.py](routes/sign_xml.py).

### Changed
- Standardized password handling across signing endpoints:
  - `key_password_b64` (Base64-encoded UTF-8 string) used for encrypted private keys.
- Updated [swaggerapi.yaml](swaggerapi.yaml) to include:
  - `/sign_link` and `/sign_xml` endpoints.
  - Full request/response schemas.
  - Algorithm selection and ECDSA formatting options.

---

## [1.0.3] - 2025-10-17

### Changed
- Disabled pretty print in JSON responses to improve integration with external systems.
- Adjusted JSON output formatting (compact mode) for cleaner API responses.

---

## [1.0.2] - 2025-10-17

### Fixed
- Improved error handling and response consistency for `/encrypt` endpoint.

---

## [1.0.1] - 2025-10-16

### Added
- Added Swagger / OpenAPI documentation [swaggerapi.yaml](swaggerapi.yaml).
- Added project documentation for external security audits (README, API specs, etc.).

---

## [1.0.0] - 2025-10-15

### Initial release
- Implemented core RSA encryption API:
  - `/encrypt` endpoint using RSAES-OAEP (MGF1 + SHA-256).
  - `/health` endpoint for monitoring.
- Added input validation and structured JSON error codes.
- Added Flask app structure with CORS and Swagger integration.
- Added [Dockerfile](Dockerfile) for containerized deployment.
- Initial repository setup and dependency list [requirements.txt](requirements.txt).

---

### Author
**KBJ DRA**  
GitHub: [tech-dra-kbj](https://github.com/tech-dra-kbj)