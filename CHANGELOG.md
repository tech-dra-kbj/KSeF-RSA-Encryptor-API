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
