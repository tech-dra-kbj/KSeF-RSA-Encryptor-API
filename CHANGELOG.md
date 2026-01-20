# 📜 CHANGELOG
**KSeF RSA Encryptor API**

_Automatically compiled from Git commit history._

---

## [1.1.0] – 2026-01-19
### Added
- Added `/sign_link` endpoint for generating **KSeF KOD II** verification links with a cryptographic signature:
  - Supported algorithms:
    - **RSA-PSS** (SHA-256, MGF1(SHA-256), salt=32, min key size 2048)
    - **ECDSA P-256** (SHA-256) with output formats:
      - **IEEE P1363** (R||S, 64 bytes) – default/recommended
      - **ASN.1 DER** (RFC 3279)
  - Accepts links with or without `https://` scheme and normalizes trailing `/`.
  - Validates that certificate public key matches the provided private key.
  - Returns a ready-to-use link with signature appended as the last path segment.

- Added `/sign_xml` endpoint for **XAdES (enveloped)** signing of XML payloads used in KSeF authentication flows.
  - Accepts input **only as Base64** (`xml_b64`, `cert_pem_b64`, `key_pem_b64`).
  - Supports algorithm selection via `alg`:
    - `rsa_sha256`
    - `ecdsa_sha256` (with P-256/secp256r1 enforcement)

### Changed
- Standardized password handling across signing endpoints:
  - `key_password_b64` (Base64(UTF-8)) used for encrypted private keys.

- Updated Swagger (`swaggerapi.yaml`) to include:
  - `/sign_link` and `/sign_xml` endpoints,
  - full request/response schemas,
  - algorithm selection and ECDSA formatting options.

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