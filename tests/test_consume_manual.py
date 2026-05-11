import base64
import json
import os

import requests

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


BASE_URL = "http://localhost:5000"
SID = "PRD001"


def pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def pkcs7_unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    return data[:-pad_len]


def aes_cbc_encrypt(aes_key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padded = pkcs7_pad(plaintext)
    return encryptor.update(padded) + encryptor.finalize()


def aes_cbc_decrypt(aes_key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return pkcs7_unpad(padded)


def rsa_oaep_encrypt(public_key, data: bytes) -> bytes:
    return public_key.encrypt(
        data,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def rsa_oaep_decrypt(private_key, ciphertext: bytes) -> bytes:
    return private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


# =========================================================
# Generate SAP RSA keypair for reply encryption
# =========================================================

sap_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

sap_public_key_pem = sap_private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

print("Generated SAP RSA keypair")


# =========================================================
# STEP 1 - GET SERVER PUBLIC KEY
# =========================================================

resp = requests.post(
    f"{BASE_URL}/get_pub_cert",
    json={"sid": SID},
    timeout=30,
)
resp.raise_for_status()

cert_data = resp.json()

print("\n/get_pub_cert response:")
print(json.dumps(cert_data, indent=2))

kid = cert_data["kid"]

server_public_key_pem = base64.b64decode(cert_data["public_key_pem_b64"])
server_public_key = serialization.load_pem_public_key(server_public_key_pem)


# =========================================================
# STEP 2 - PREPARE INTERNAL PAYLOAD
# =========================================================

internal_payload = {
    "target": "/encrypt",
    "payload": {
        "data_b64": base64.b64encode(b"HELLO FROM SAP").decode("ascii"),
        "cert_b64": base64.b64encode(server_public_key_pem).decode("ascii"),
        "return_b64": True,
    },
}

internal_payload_json = json.dumps(
    internal_payload,
    separators=(",", ":"),
).encode("utf-8")

print("\nInternal plaintext payload:")
print(internal_payload_json.decode("utf-8"))


# =========================================================
# STEP 3 - HYBRID ENCRYPTION
# =========================================================

aes_key = os.urandom(32)
iv = os.urandom(16)

ciphertext = aes_cbc_encrypt(
    aes_key,
    iv,
    internal_payload_json,
)

enc_key = rsa_oaep_encrypt(
    server_public_key,
    aes_key,
)

print("\nPayload encrypted")


# =========================================================
# STEP 4 - CALL /consume
# =========================================================

consume_payload = {
    "sid": SID,
    "kid": kid,
    "enc_key_b64": base64.b64encode(enc_key).decode("ascii"),
    "iv_b64": base64.b64encode(iv).decode("ascii"),
    "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    "reply_public_key_pem_b64": base64.b64encode(sap_public_key_pem).decode("ascii"),
}

resp = requests.post(
    f"{BASE_URL}/consume",
    json=consume_payload,
    timeout=30,
)

print("\n/consume status:", resp.status_code)
print(resp.text)

resp.raise_for_status()

consume_response = resp.json()
reply = consume_response["reply"]


# =========================================================
# STEP 5 - DECRYPT SERVER RESPONSE
# =========================================================

reply_enc_key = base64.b64decode(reply["enc_key_b64"])
reply_iv = base64.b64decode(reply["iv_b64"])
reply_ciphertext = base64.b64decode(reply["ciphertext_b64"])

reply_aes_key = rsa_oaep_decrypt(
    sap_private_key,
    reply_enc_key,
)

reply_plaintext = aes_cbc_decrypt(
    reply_aes_key,
    reply_iv,
    reply_ciphertext,
)

print("\nDecrypted server reply:")
print(reply_plaintext.decode("utf-8"))

print("\nSUCCESS")