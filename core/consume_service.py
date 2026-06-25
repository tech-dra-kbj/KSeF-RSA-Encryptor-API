import base64
import json
import secrets

from core.crypto_utils import (
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    cms_decrypt_with_key,
    cms_encrypt_with_cert,
)
from core.key_manager import get_certificate_pem_for_kid, get_private_key_pem_for_kid
from core.ksef_encrypt import encrypt_rsa_oaep, load_ksef_public_key_from_string


def decrypt_request(payload: dict) -> dict:
    sid = payload["sid"]
    kid = payload["kid"]

    enveloped_der = base64.b64decode(payload["enc_key_b64"])
    iv = base64.b64decode(payload["iv_b64"])
    ciphertext = base64.b64decode(payload["ciphertext_b64"])

    private_key_pem = get_private_key_pem_for_kid(sid, kid)
    certificate_pem = get_certificate_pem_for_kid(sid, kid)

    aes_key = cms_decrypt_with_key(enveloped_der, certificate_pem, private_key_pem)

    plaintext = aes_cbc_decrypt(aes_key, iv, ciphertext)

    return {"plaintext": plaintext}


def dispatch(plaintext: bytes) -> bytes:
    try:
        request_obj = json.loads(plaintext.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid plaintext JSON: {exc}") from exc

    if not isinstance(request_obj, dict):
        raise ValueError("Plaintext must be a JSON object.")

    target = request_obj.get("target")
    inner_payload = request_obj.get("payload") or {}

    if not isinstance(inner_payload, dict):
        raise ValueError("'payload' must be a JSON object.")

    if target == "/encrypt":
        return _handle_encrypt(inner_payload)

    raise ValueError(f"Unknown target: {target!r}")


def _handle_encrypt(payload: dict) -> bytes:
    data_b64 = payload.get("data_b64")
    cert_b64 = payload.get("cert_b64")

    if not data_b64 or not cert_b64:
        raise ValueError("Missing 'data_b64' or 'cert_b64' in /encrypt payload.")

    data = base64.b64decode(data_b64)
    public_key = load_ksef_public_key_from_string(cert_b64)
    encrypted = encrypt_rsa_oaep(public_key, data)

    result = json.dumps(
        {"status": "ok", "encrypted_b64": base64.b64encode(encrypted).decode("ascii")},
        separators=(",", ":"),
    )
    return result.encode("utf-8")


def encrypt_response(plaintext: bytes, reply_cert_pem_b64: str) -> dict:
    reply_cert_pem = base64.b64decode(reply_cert_pem_b64)

    aes_key = secrets.token_bytes(32)
    iv = secrets.token_bytes(16)

    ciphertext = aes_cbc_encrypt(aes_key, iv, plaintext)
    enveloped_der = cms_encrypt_with_cert(aes_key, reply_cert_pem)

    return {
        "enc_key_b64": base64.b64encode(enveloped_der).decode("ascii"),
        "iv_b64": base64.b64encode(iv).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    }
