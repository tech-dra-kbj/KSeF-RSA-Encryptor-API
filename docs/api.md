# API Endpoints Reference

Interactive documentation: `http://localhost:5000/apidocs`

---

## `GET /`

Returns service metadata and available endpoints.

**Response:**
```json
{
  "service": "KSeF Integration API 1.3.0",
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
  "version": "1.3.0"
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
    "nrKSeF": "20260101-1234567890-ABCDEF1234567890",
    "qrCode": "https://...",
    "isMobile": false
  }
}
```

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

Secure encrypted tunnel. Accepts a CMS-wrapped payload, decrypts it, executes the inner request against a local endpoint (e.g. `/encrypt`), and returns an encrypted response.

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
