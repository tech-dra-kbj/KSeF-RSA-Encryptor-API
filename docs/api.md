# API Endpoints Reference

Interactive documentation: `http://localhost:5000/apidocs`

---

## Base64 fields

Every `*_b64` field is decoded the same way across all endpoints:

- **Line wrapping is accepted.** Whitespace, `\n` and `\r\n` are stripped before
  decoding, so Base64 wrapped at 64 or 76 characters — what ABAP, OpenSSL and anything
  that has passed through PEM produce — works unchanged.
- **Anything else is rejected.** A character outside the Base64 alphabet fails the
  request instead of being silently dropped, so a payload corrupted in transit can
  never be encrypted or signed as a shorter — or empty — value.

---

## Error codes

Endpoints that return a numeric `code` use one envelope:

```json
{"status": "error", "code": 2202, "message": "..."}
```

**Decide whether to retry from the HTTP status, not the code.** `4xx` means the request
must change and will fail again unchanged; `5xx` is worth retrying. The `code` exists so
a caller can report *why* without parsing prose. Codes are never reused, and each
endpoint owns a numeric block whose `x99` is reserved for "unexpected".

| Block | Endpoint | Documented under |
|---|---|---|
| `1xx` | `/encrypt` | [`POST /encrypt`](#post-encrypt) |
| `21xx` – `23xx` | `/generatePDF` | [`POST /generatePDF`](#post-generatepdf) |

Endpoints not listed above — `/sign_xml`, `/sign_link`, `/get_pub_cert`, `/consume` —
do not carry a `code` yet. They return `{"error": "<message>"}` with an appropriate HTTP
status, so branch on the status and treat the message as human-readable only. Blocks
`3xx` and up are unallocated and reserved for them.

---

## `GET /`

Returns service metadata and available endpoints.

**Response:**
```json
{
  "service": "KSeF Integration API 1.4.0",
  "docs": "/apidocs",
  "health": "/health",
  "generate_pdf": "/generatePDF"
}
```

---

## `GET /health`

Health check for monitoring and container probes.

**Response:**
```json
{
  "status": "ok",
  "service": "KSeF Integration API",
  "version": "1.4.0"
}
```

---

## `POST /encrypt`

Encrypts a payload using **RSAES-OAEP (MGF1 + SHA-256)** with the public key from a KSeF certificate.

**Request:**
```json
{
  "data_b64": "ZGFuZV9pbnB1dA==",
  "cert_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBC..."
}
```

**Response:**
```json
{
  "status": "ok",
  "encrypted_b64": "eGlkY2FlYmQ5Mm..."
}
```

### Errors

Same envelope as [`/generatePDF`](#post-generatepdf), with the 1xx block:

| Code | Status | Cause |
|---|---|---|
| `101` | `400` | `data_b64` or `cert_b64` missing or empty |
| `102` | `400` | `data_b64` is not valid Base64 |
| `103` | `400` | `cert_b64` could not be read as a certificate or public key |
| `104` | `500` | RSAES-OAEP encryption failed |
| `199` | `500` | Unexpected error |

This endpoint predates the shared envelope and does not carry the deprecated `error`
alias — it returns `status`, `code` and `message` only.

---

## `POST /sign_xml`

Signs an XML payload using **XAdES enveloped** signature.

**Request:**
```json
{
  "xml_b64": "PEF1dGhUb2tlblJlcXVlc3Q+Li4uPC9BdXRoVG9rZW5SZXF1ZXN0Pg==",
  "cert_pem_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
  "key_pem_b64": "LS0tLS1CRUdJTiBFTkNSWVBURUQgUFJJVkFURSBLRVktLS0tLQ==",
  "key_password_b64": "emFxMUBXU1hjZGUzJFJGVg==",
  "alg": "rsa_sha256"
}
```

`alg`: `rsa_sha256` (default) or `ecdsa_sha256`

**Response:**
```json
{
  "signed_xml_b64": "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4...",
  "alg_used": "rsa_sha256"
}
```

---

## `POST /sign_link`

Signs a KSeF offline QR verification link.

**Request:**
```json
{
  "link_b64": "cXItZGVtby5rc2VmLm1mLmdvdi5wbC9jZXJ0aWZpY2F0ZS9OaXAvODExM...",
  "cert_pem_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...",
  "key_pem_b64": "LS0tLS1CRUdJTiBFTkNSWVBURUQgUFJJVkFURSBLRVktLS0tLQ==",
  "key_password_b64": "emFxMUBXU1hjZGUzJFJGVg==",
  "alg": "rsa_pss",
  "ecdsa_format": "p1363"
}
```

`alg`: `rsa_pss` (default) or `ecdsa_p256`  
`ecdsa_format`: `p1363` (default, R||S 64 bytes) or `der`

The private key password may be given either way:

| Field | Description |
|---|---|
| `key_password_b64` | Password as Base64(UTF-8). Takes precedence when both are present |
| `key_password` | Password as plain UTF-8 text. **Accepted only by this endpoint** — `/sign_xml` takes `key_password_b64` exclusively |

**Response:**
```json
{
  "link_b64": "aHR0cHM6Ly9xci1kZW1vLmtzZWYubWYuZ292LnBsL2Nl...",
  "alg_used": "rsa_pss",
  "ecdsa_format_used": null
}
```

---

## `POST /generatePDF`

Renders an invoice PDF from XML using the Node.js bridge.

**Request:**
```json
{
  "xml_b64": "PEF1dGhUb2tlblJlcXVlc3Q+Li4u",
  "response_type": "base64",
  "additional_data": {
    "nr_ksef": "20260101-1234567890-ABCDEF1234567890",
    "ac_date": "2026-01-01T12:00:00Z",
    "qr_code": "https://...",
    "qr2_code": "https://...",
    "is_mobile": false,
    "watermark": "KOPIA",
    "language": "pl"
  }
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `xml_b64` | string | **yes** | — | Invoice XML encoded as Base64 |
| `response_type` | string | no | `base64` | `base64` — JSON with `pdf_b64`, `binary` — raw PDF |
| `additional_data.nr_ksef` | string | no | — | KSeF number printed on the PDF |
| `additional_data.ac_date` | string | no | — | Date the KSeF number was assigned, printed next to it |
| `additional_data.qr_code` | string | no | — | QR code URL |
| `additional_data.qr2_code` | string | no | — | Second QR code URL |
| `additional_data.is_mobile` | bool | no | — | Mobile layout variant |
| `additional_data.watermark` | string | no | — | Watermark text on every page (e.g. `KOPIA`, `ANULOWANA`) |
| `additional_data.language` | string | no | `pl` | PDF label language: `pl` or `en` (case-insensitive). See note below. |

> **Note:** the Ministry publishes no official English wording for KSeF invoice field labels, so `language: en` uses this project's own translation, reviewed and corrected by a consultant. It is maintained in [`pdf-generator/i18n/en.json`](../pdf-generator/i18n/en.json) — see [Architecture](architecture.md#rebuilding-the-pdf-generator) before rebuilding the generator.

`response_type`: `base64` (default) or `binary`

**Response (base64):**
```json
{
  "status": "ok",
  "pdf_b64": "JVBERi0xLjQKJcTl8uXr..."
}
```

**Response (binary):** `Content-Type: application/pdf`

```bash
curl -X POST http://localhost:5000/generatePDF \
  -H "Content-Type: application/json" \
  -d '{"xml_b64":"PEF1dGhUb2tlblJlcXVlc3Q+Li4u","response_type":"binary"}' \
  --output invoice.pdf
```

### Errors

Every failure returns the same envelope, the one `/encrypt` uses:

```json
{
  "status": "error",
  "code": 2202,
  "message": "XML is not a recognised KSeF invoice document: Unknown XML Version: undefined",
  "error": "XML is not a recognised KSeF invoice document: Unknown XML Version: undefined"
}
```

`error` repeats `message` for callers written against the previous contract. It is
deprecated; read `code`.

**Decide whether to retry from the HTTP status, not the code.** `400` means the request
must change and will fail again unchanged. `504` is worth retrying. `500` is worth
retrying with backoff. The `code` exists so a caller can report *why* without parsing
prose, and codes are never reused.

#### `400` — the caller must fix the request

Request validation (21xx):

| Code | Cause |
|---|---|
| `2100` | Body is not a JSON object |
| `2101` | Body is not valid JSON |
| `2102` | `xml_b64` missing, empty, or not a string |
| `2103` | `xml_b64` is not valid Base64 |
| `2104` | Decoded bytes are not UTF-8 text |
| `2105` | `response_type` is neither `base64` nor `binary` |
| `2106` | `additional_data` is not an object |
| `2107` | `additional_data.language` is neither `pl` nor `en` |

XML payload (22xx):

| Code | Cause |
|---|---|
| `2200` | Decoded content holds no XML |
| `2201` | XML is not well-formed — `message` carries the parser's line and column |
| `2202` | XML is not a recognised KSeF invoice document (FA(1), FA(2), FA(3), FA_RR) |

#### `500` / `504` — the service could not complete the request

| Code | Status | Cause |
|---|---|---|
| `2300` | `504` | Generation exceeded `KSEF_PDF_TIMEOUT_SECONDS` (60 s by default) |
| `2301` | `500` | Node.js runtime unavailable |
| `2302` | `500` | Generator returned an unreadable response |
| `2303` | `500` | Generator returned empty output |
| `2399` | `500` | Unexpected error |

A generator failure whose message the service does not recognise is reported as `2399`,
not as a payload error. Attributing an unknown fault to the caller would stop them
retrying something a retry could clear. The recognised patterns live in
[`core/pdf_errors.py`](../core/pdf_errors.py).

#### Responses that do not use this envelope

Two cases never reach the application, so they carry neither `code` nor JSON:

| Situation | Response |
|---|---|
| Request body over `KSEF_SSL_MAX_BODY` (15 MB by default) | `413` from nginx, **HTML** body |
| No TLS proxy reachable | connection error, no HTTP response |

Branch on `Content-Type` rather than assuming JSON. On success with
`response_type: binary` the reply is `application/pdf`; on failure it is
`application/json`.

---

## `POST /get_pub_cert`

Generates or retrieves an active RSA keypair and self-signed certificate for a given System ID (`sid`). Used to establish credentials for the `/consume` tunnel.

**Request:**
```json
{
  "sid": "SYS123"
}
```

`sid` format: `^[A-Z0-9]{6}$`

**Response:**
```json
{
  "sid": "SYS123",
  "kid": "8d3cfb5b-21fb-4e1b-9fca-5777df50ad6d",
  "created_at": 1714560000,
  "expires_at": 1714646400,
  "public_key_pem_b64": "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0...",
  "public_cert_pem_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t..."
}
```

---

## `POST /consume`

Secure encrypted tunnel. Accepts a CMS-wrapped payload, decrypts it, executes the inner request, and returns the result as plaintext or encrypted with the client's certificate.

**Payload wrapping flow:**
```
[JSON plaintext] → AES-256-CBC (random key + IV)
  ├── AES key wrapped in CMS using the SID's public certificate
  └── enc_key_b64 + iv_b64 + ciphertext_b64 sent in request
```

**Request:**
```json
{
  "sid": "SYS123",
  "kid": "8d3cfb5b-21fb-4e1b-9fca-5777df50ad6d",
  "enc_key_b64": "MIIByQYJKoZIhvcNAQcDoIIBujCCAbYCAQA...",
  "iv_b64": "cGFzc3dvcmQxMjM0NTY3OA==",
  "ciphertext_b64": "Y2lwaGVydGV4dF9zb21ldGhpbmc=",
  "reply_cert_pem_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t..."
}
```

`reply_cert_pem_b64` is optional. When provided, the response is encrypted with the client's certificate.

**Structure of the encrypted plaintext.** This is the JSON that `ciphertext_b64` must decrypt to — build it before encrypting:

```json
{
  "target": "/encrypt",
  "payload": {
    "data_b64": "SGVsbG8gS1NlRg==",
    "cert_b64": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t..."
  }
}
```

| Field | Description |
|---|---|
| `target` | Operation to run. **`/encrypt` is currently the only supported value** — anything else fails with `Dispatch error: Unknown target: ...` |
| `payload` | That operation's own fields. For `/encrypt`: `data_b64` and `cert_b64`, exactly as the plain endpoint takes them |

The decrypted response is whatever that operation would have returned, e.g. `{"status":"ok","encrypted_b64":"..."}`.

> The key transport algorithm inside the CMS envelope is RSAES-PKCS1-v1_5 (OpenSSL's default for `cms -encrypt`), not RSAES-OAEP. See [Architecture](architecture.md#cryptographic-specifications).

**Response (no reply cert):**
```json
{
  "status": "ok",
  "plaintext_b64": "eyJzdGF0dXMiOiJvayIsImVuY3J5cHRlZF9iNjQiOiIuLi4ifQ=="
}
```

**Response (with reply cert):**
```json
{
  "status": "ok",
  "reply": {
    "enc_key_b64": "MIIByQYJKoZI...",
    "iv_b64": "cGFzc...",
    "ciphertext_b64": "Y2lwaGVy..."
  }
}
```
