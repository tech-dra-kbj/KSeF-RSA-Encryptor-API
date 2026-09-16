# Changelog

All notable changes to the KSeF Integration API project will be documented in this file.

---

## [1.3.3] - 2026-09-16

### Security
- Removed `curl` and `libcurl` from the application image entirely, in response to a vulnerability report from a customer's IT security team. The reported curl finding was a false positive — Debian backports security fixes without bumping the upstream version, and the package reported itself as `security patched: 8.14.1-2+deb13u4` — but curl turned out to be unnecessary at runtime: `libcurl4t64` had `curl` as its only reverse dependency, `node` does not link it, the healthcheck goes through Python's `urllib`, and the application makes no outbound connections. It is now purged right after the NodeSource setup script that needs it, which removes the whole class of findings from the image rather than chasing versions. `apt-get upgrade` in the build layer also took OpenSSL 3.5.6 → 3.5.7.
- Rebuilt the TLS proxy on a current base. The `nginx:1.27-alpine` pin had gone stale on Alpine 3.21 and carried about twenty outdated packages, curl among them at 8.12.1 (February 2025) — this part of the report was accurate. Now `nginx:1.30-alpine` (the stable branch, floating minor so rebuilds pick up patch releases) plus `apk upgrade --no-cache`: curl 8.22.0, OpenSSL 3.5.8, nginx 1.30.5, and 0 packages pending upgrade.
- Still open after this release: `pyOpenSSL` 23.2.0 and `cryptography` 41.0.7 are due for an upgrade. `cryptography` statically links its own OpenSSL 3.1.4, a branch EOL since March 2025, so no OS-level update reaches it. `signxml` sets no upper bound on either, but it backs XAdES signing, so the bump ships as a separate release after signing regression tests.

### Changed
- Updated PDF generator to **v1.1.36** (`ksef-fe-invoice-converter`, built from [CIRFMF/ksef-pdf-generator](https://github.com/CIRFMF/ksef-pdf-generator) tag `1.1.36`). Upstream bumped `pdfmake` 0.3.7 → 0.3.11, made `formatText` render an explicit `0` instead of dropping it, made `hasValue` null-safe, and removed the unused PEF layout helpers. The public API is unchanged, so `pdf_generator_bridge.mjs` needed no changes. A rendered FA (3) invoice is byte-for-byte identical to the 1.1.31 output apart from the generator version printed in the footer.

### Fixed
- English terminology consistency, from an audit of all 997 keys plus every schema vocabulary in upstream's `FA.const.ts`. `Nabywca` rendered as both `Purchaser` and `buyer` on the same invoice — the party section header read **Purchaser** while `Buyer's bank account` appeared a few lines below; unified to `Buyer` / `Buyer identifier: ` across 9 keys, matching EN 16931 BT-44 and the English KSeF documentation. The two correction labels had drifted from the labels they correct: `Korekta kwoty należności ogółem:` read `Adjustment of the total amount receivable:` next to `Total amount due:`, and `Korekta kwoty pozostałej do zapłaty:` read `Adjustment of the remaining amount:` next to `Outstanding amount:`; both now use `Correction of …` with the matching noun. `invoice.discount.unit` was still `Unit` while the other two "Miara" keys had become `Unit of measure`. After the pass `nabywca` maps to *buyer* 24 times and *purchaser* zero, `korekta` to *correction* 13 times and *adjustment* zero, and no schema vocabulary has two codes sharing one English label.
- 7 English translations from a second consultant pass (`missing_poprawioneJW.csv`): `const.fa.bubble` "Bańka" → `Jug`, `invoice.rows.unit` and `invoice.order.unit` "Miara" → `Unit of measure`, `invoice.payment.paidInPart` → `Partially paid`, `invoice.payment.paymentMethod3` → `Method of payment: `, and two `pef.invoiceHeader` keys. The consultant gave `paymentMethod3` without its colon; the Polish source is `'Forma zapłaty: '` and the generator concatenates label and value with no separator, so the wording was taken and the punctuation kept. The sheet had been generated from the pre-sweep file, so a blank row means unreviewed rather than approved.
- 178 English translations, after reviewing all 997 keys against upstream `pl.json`. Domain vocabularies were verified through upstream's own schema mapping (`src/shared/consts/FA.const.ts`), which binds each FA XML code to a translation key, so every label was checked against what it represents in the schema rather than against the Polish wording alone.
- 69 labels lost the trailing space that PL carries. The generator concatenates label and value without a separator, so English invoices printed `Invoice number:FA/123`, `GV group:NO` and `National Systeme-Invoices`. English whitespace now mirrors Polish for all 997 keys.
- Packaging codes (`TypLadunku`). Three pairs shared one English label and could not be told apart on an invoice: "Pojemnik" and "Kontener" were both `Container`, "Paczka" and "Pakiet" both mapped to package wording, and "Kosz/koszyk" read `Basket/basket`. "Bańka" — a metal vessel for liquids — read `Bubble`, and "Łubianka" read `Lubyanka`.
- Tax rate codes (`TStawkaPodatku_FA3`). The schema's Polish codes were translated as if they were ordinary words and are printed in the tax rate column: `zw` read `conv`, `oo` read `oh`, and `np` ("niepodlegające opodatkowaniu") read `e.g.` across four keys.
- Taxpayer status (`TAXPAYER_STATUS`). Two of the four values carried a trailing "status", so the invoice printed `Taxpayer status: Bankruptcy status`. "Postępowanie restrukturyzacyjne" also read `Restructuring proces`.
- `PKOB` (the Polish classification of building structures) read `GDP` in three column headers, `invoice.payment.other` was left untranslated as `Inna`, "Numer nadwozia" and "Numer podwozia" shared `Chassis number`, and "Dane faktury korygowanej" read `Correction invoice details`, reversing which invoice it refers to.
- Statutory references. Polish "ust." and "pkt" were both rendered `sec.`, producing `Article 100 sec. 1 sec. 4`; "pkt" is now `point`. `invoice.details.issueDate`, printed on every invoice, read `of the The Goods and Services Tax Act`.
- `invoice.*.unit` ("Miara", the unit-of-measure column header) read `Standard`, next to a `Tax rate` column; `invoice.footer.pagesTotal` ("z", as in "1 z 3") read `With`, so the footer printed `1 With 3`.
- Not fixable from `en.json`, and still present upstream in 1.1.36: `PDF-functions.ts:615` returns a hardcoded `'marża'` that bypasses i18n, so margin invoices print Polish even with `language: en`; `pef.after` and `pef.before` are swapped; `RodzajTransportu` has no mapping for code `6`.

### Added
- 39 English translations in `pdf-generator/i18n/en.json`, all in the `pef` namespace: the 20 keys upstream added in 1.1.36 (`accountingCost`, `invoiceDocumentReference`, `issuer`, `receiverParty`, `settlementAmount`, `additionalInvoiceGrossData`, and the ten `taxCategory` codes, which use the official UNCL5305 English names), plus 19 keys that upstream ships in `pl.json` but has never had in `en.json` at all (`accountReckoning`, `diffSummary`, `before`/`after`, `from`/`to`, `sum`, `invoiceLine.grossAmount`, `invoiceLine.taxVat`). The file is now built against the `pl.json` key skeleton, so it covers all 997 keys; the 958 existing translations are unchanged. None of these keys is reachable from a KSeF FA invoice — the PEF generator is not part of the public upstream build.

---

## [1.3.2] - 2026-08-27

### Fixed
- English PDF labels. Upstream ships `en.json` filled with `ExampleText` placeholders, so the 1.1.31 rebuild in 1.3.1 produced English invoices in which every label read `ExampleText` — 80 occurrences in a single generated PDF. The generator was rebuilt with a translation reviewed and corrected by a consultant; a regenerated EN invoice now contains none.

### Added
- `pdf-generator/i18n/en.json` — the maintained English translation, kept in the repository as the source of truth and reapplied on every generator rebuild. `docs/architecture.md` documents the procedure and the `grep -c ExampleText` check that catches a skipped reapplication.
- Optional TLS termination for production via `docker/docker-compose.ssl.yml` — an additive overlay that stacks onto the existing compose files and changes nothing in them; the application container keeps publishing port 5000 on the host. Adds `ksef-ssl-proxy` (nginx-alpine, ~85 MB) on 443, with 80 redirecting to it.
- The proxy provisions its own TLS material on first start and writes it to `docker/certs/` on the host, so it survives redeploys and `ca.crt` can be handed to clients. An existing `server.crt`/`server.key` pair is always reused, so a certificate from your own PKI is picked up and never overwritten; a locally issued certificate that has expired is renewed automatically, anything else is left alone with a warning. A mismatched certificate/key pair aborts startup with an explicit error.
- TLS 1.2 is the primary target, with 1.3 available for clients that support it and 1.0/1.1 refused. The TLS 1.2 cipher list is ECDHE-only and includes CBC-SHA suites for older Java/SAP stacks. Protocols, ciphers, SAN entries, body limit and certificate validity are configurable per deployment — see docs/deployment.md.

### Changed
- Documentation no longer describes English as a GPT-generated test feature.
- Updated PDF generator to **v1.1.31** (`ksef-fe-invoice-converter`, built from [CIRFMF/ksef-pdf-generator](https://github.com/CIRFMF/ksef-pdf-generator) tag `1.1.31`).
- Updated `pdf_generator_bridge.mjs`: replaced the locally patched `generateInvoiceFromXml` with upstream `generateInvoice` + a `FileReader` polyfill for Node.js compatibility; redirected module console output to stderr so i18next debug logs no longer corrupt the stdout JSON.
- Added `additional_data.watermark` — optional watermark text printed on every page of the generated PDF.
- Added `additional_data.language` — PDF label language (`pl` / `en`, default `pl`, case-insensitive).
- Added `additional_data.ac_date` — date the KSeF number was assigned (upstream 1.1.25).
- `/generatePDF` error responses now carry the generator's actual error instead of i18next debug output; the bridge marks its own failure on stderr and `core/pdf_service.py` extracts it.
- Added `.dockerignore` — the upstream generator source clone (`ksef-pdf-generator/`, ~229 MB with `node_modules`) and other non-runtime files no longer enter the Docker build context, which shrinks it to ~5.5 MB.
- Moved every Docker artifact into `docker/`: `Dockerfile`, the three compose files, `build-image.sh`, and the build-context excludes (now `docker/Dockerfile.dockerignore`, which BuildKit resolves from the Dockerfile's path). Compose builds with `context: ..` and pins `name: ksef-integration-api` so the project keeps one identity regardless of the invoking directory. `setup-ssl.sh` stays at the repository root — it also covers systemd deployments. Commands gain a `docker/` prefix, e.g. `docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d`.
- Documentation audit against the code. `/consume` now documents the structure of the encrypted plaintext (`target` / `payload`) that clients must produce — previously only the outer envelope was described, which left the endpoint unusable from the docs alone — and states that `/encrypt` is its only supported target. `/sign_link` documents the plaintext `key_password` field it accepts. Swagger response codes were reconciled with the handlers: 500 added to `/get_pub_cert` and `/consume`, removed from `/sign_xml` and `/sign_link`, whose catch-all returns 400. Corrected the CMS key transport algorithm in `docs/architecture.md` from RSAES-OAEP to RSAES-PKCS1-v1_5, which is what `openssl cms -encrypt` actually produces. Refreshed stale 1.3.0 `/health` samples.
- Updated `tests/test_routes.py` version assertions and stopped pytest from collecting `tests/test_consume_manual.py`, a manual script that needs a live service and the non-dependency `requests`.

### Upstream PDF generator changes included (1.1.19 → 1.1.31)
- All line items of an invoice position are now rendered in a collective correction (1.1.31).
- Field `P_15` is always visualized (1.1.31).
- Added `configureFonts()` for registering custom fonts; unified decimal separators for OSS and ZZP tax rates; corrected `UU_IDZ` description and date formatting in annotations (1.1.30).
- Added KSeF number assignment date; removed a spurious blank page at the end of the invoice; added currency code to order/prepayment summaries (1.1.25).

---

## [1.3.1] - 2026-06-25

Released from `de5be91`. Superseded by 1.3.2 — the items originally drafted under this
heading were never part of the published v1.3.1 and have been moved to 1.3.2.

### Changed
- Updated PDF generator to v1.1.19 (`ksef-fe-invoice-converter`).
- Updated `pdf_generator_bridge.mjs`: replaced removed `generateInvoiceFromXml` with `generateInvoice` + `FileReader` polyfill for Node.js compatibility; redirected module console output to stderr.
- Added `additional_data.watermark` — optional watermark text printed on every page of the generated PDF.
- Added `additional_data.language` — PDF label language (`pl` / `en`, default `pl`, case-insensitive).
- Fixed gunicorn `--preload` to prevent a SQLite lock during worker init.

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