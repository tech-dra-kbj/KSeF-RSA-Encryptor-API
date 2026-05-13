"""
Manual integration test against a running local server.
Run: python tests/test_consume_manual.py
"""
import base64
import json
import os

import requests

from core.crypto_utils import (
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    cms_decrypt_with_key,
    cms_encrypt_with_cert,
    generate_rsa_keypair,
    generate_self_signed_certificate,
    serialize_certificate_pem,
    serialize_private_key_pem,
)

BASE_URL = "http://localhost:5000"
SID = "PRD001"


def main():
    # =========================================================
    # Generate SAP keypair + self-signed cert for reply channel
    # =========================================================

    sap_private_key = generate_rsa_keypair()
    sap_cert_pem = serialize_certificate_pem(generate_self_signed_certificate(sap_private_key))
    sap_private_key_pem = serialize_private_key_pem(sap_private_key)

    print("Generated SAP RSA keypair + certificate")

    # =========================================================
    # STEP 1 — GET SERVER CERTIFICATE
    # =========================================================

    resp = requests.post(f"{BASE_URL}/get_pub_cert", json={"sid": SID}, timeout=30)
    resp.raise_for_status()

    cert_data = resp.json()
    print("\n/get_pub_cert response:")
    print(json.dumps(
        {k: v for k, v in cert_data.items() if k not in ("public_key_pem_b64", "public_cert_pem_b64")},
        indent=2,
    ))

    kid = cert_data["kid"]
    server_cert_pem = base64.b64decode(cert_data["public_cert_pem_b64"])

    # =========================================================
    # STEP 2 — BUILD INTERNAL PAYLOAD
    # =========================================================

    internal_payload = {
        "target": "/encrypt",
        "payload": {
            "data_b64": base64.b64encode(b"HELLO FROM SAP").decode("ascii"),
            "cert_b64": base64.b64encode(server_cert_pem).decode("ascii"),
        },
    }

    plaintext_bytes = json.dumps(internal_payload, separators=(",", ":")).encode("utf-8")

    print("\nInternal plaintext payload:")
    print(json.dumps(internal_payload, indent=2))

    # =========================================================
    # STEP 3 — HYBRID ENCRYPTION (CMS + AES-CBC)
    # =========================================================

    aes_key = os.urandom(32)
    iv = os.urandom(16)

    ciphertext = aes_cbc_encrypt(aes_key, iv, plaintext_bytes)
    enveloped_der = cms_encrypt_with_cert(aes_key, server_cert_pem)

    print("\nPayload encrypted (CMS envelope + AES-256-CBC)")

    # =========================================================
    # STEP 4 — CALL /consume
    # =========================================================

    consume_payload = {
        "sid": SID,
        "kid": kid,
        "enc_key_b64": base64.b64encode(enveloped_der).decode("ascii"),
        "iv_b64": base64.b64encode(iv).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "reply_cert_pem_b64": base64.b64encode(sap_cert_pem).decode("ascii"),
    }

    resp = requests.post(f"{BASE_URL}/consume", json=consume_payload, timeout=30)

    print("\n/consume status:", resp.status_code)
    resp.raise_for_status()

    consume_response = resp.json()
    reply = consume_response["reply"]

    # =========================================================
    # STEP 5 — DECRYPT SERVER RESPONSE (CMS + AES-CBC)
    # =========================================================

    reply_enveloped_der = base64.b64decode(reply["enc_key_b64"])
    reply_iv = base64.b64decode(reply["iv_b64"])
    reply_ciphertext = base64.b64decode(reply["ciphertext_b64"])

    reply_aes_key = cms_decrypt_with_key(reply_enveloped_der, sap_cert_pem, sap_private_key_pem)

    reply_plaintext = aes_cbc_decrypt(reply_aes_key, reply_iv, reply_ciphertext)

    print("\nDecrypted server reply:")
    print(reply_plaintext.decode("utf-8"))

    print("\nSUCCESS")


if __name__ == "__main__":
    main()
