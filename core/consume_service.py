import base64
import secrets

from core.crypto_utils import (
    load_private_key_pem,
    load_public_key_pem,
    rsa_oaep_decrypt,
    rsa_oaep_encrypt,
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    verify_hmac_sha256,
    compute_hmac_sha256,
)

from core.key_manager import get_private_key_pem_for_kid


def decrypt_request(payload: dict) -> dict:
    sid = payload["sid"]
    kid = payload["kid"]

    enc_key = base64.b64decode(payload["enc_key_b64"])
    iv = base64.b64decode(payload["iv_b64"])
    ciphertext = base64.b64decode(payload["ciphertext_b64"])
    mac = base64.b64decode(payload["hmac_b64"])

    # 1. load private key
    private_key_pem = get_private_key_pem_for_kid(sid, kid)
    private_key = load_private_key_pem(private_key_pem)

    # 2. decrypt AES key
    aes_key = rsa_oaep_decrypt(private_key, enc_key)

    # 3. verify HMAC (Encrypt-then-MAC)
    verify_hmac_sha256(aes_key, iv + ciphertext, mac)

    # 4. decrypt payload
    plaintext = aes_cbc_decrypt(aes_key, iv, ciphertext)

    return {
        "plaintext": plaintext,
        "aes_key": aes_key,  # needed for response if symmetric reuse (optional)
    }


def encrypt_response(plaintext: bytes, reply_public_key_pem_b64: str) -> dict:
    reply_pub_pem = base64.b64decode(reply_public_key_pem_b64)
    reply_pub = load_public_key_pem(reply_pub_pem)

    aes_key = secrets.token_bytes(32)
    iv = secrets.token_bytes(16)

    ciphertext = aes_cbc_encrypt(aes_key, iv, plaintext)
    mac = compute_hmac_sha256(aes_key, iv + ciphertext)
    enc_key = rsa_oaep_encrypt(reply_pub, aes_key)

    return {
        "enc_key_b64": base64.b64encode(enc_key).decode(),
        "iv_b64": base64.b64encode(iv).decode(),
        "ciphertext_b64": base64.b64encode(ciphertext).decode(),
        "hmac_b64": base64.b64encode(mac).decode(),
    }