import base64
import os
import tempfile

import pytest

import core.config as config
import core.database as database
import encrypt_service
from core.crypto_utils import (
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    generate_rsa_keypair,
    load_public_key_pem,
    rsa_oaep_decrypt,
    rsa_oaep_encrypt,
    serialize_public_key_pem,
)


@pytest.fixture
def client(monkeypatch):
    """
    Create Flask test client with isolated temporary SQLite database.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        monkeypatch.setattr(config, "DB_PATH", db_path)
        monkeypatch.setattr(database, "DB_PATH", db_path)

        app = encrypt_service.create_app()
        app.config.update(TESTING=True)

        with app.test_client() as test_client:
            yield test_client


def test_consume_decrypts_payload_roundtrip(client):
    key_response = client.post(
        "/get_pub_cert",
        json={"sid": "PRD001"},
    )

    assert key_response.status_code == 200

    key_data = key_response.get_json()
    sid = key_data["sid"]
    kid = key_data["kid"]

    public_key_pem = base64.b64decode(key_data["public_key_pem_b64"])
    public_key = load_public_key_pem(public_key_pem)

    plaintext = b'{"hello":"world","amount":123.45}'

    aes_key = os.urandom(32)
    iv = os.urandom(16)

    ciphertext = aes_cbc_encrypt(aes_key, iv, plaintext)
    enc_key = rsa_oaep_encrypt(public_key, aes_key)

    response = client.post(
        "/consume",
        json={
            "sid": sid,
            "kid": kid,
            "enc_key_b64": base64.b64encode(enc_key).decode("ascii"),
            "iv_b64": base64.b64encode(iv).decode("ascii"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        },
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ok"

    decrypted = base64.b64decode(data["plaintext_b64"])
    assert decrypted == plaintext


def test_consume_rejects_missing_fields(client):
    response = client.post(
        "/consume",
        json={
            "sid": "PRD001",
        },
    )

    assert response.status_code == 400

    data = response.get_json()
    assert "error" in data


def test_consume_rejects_invalid_ciphertext(client):
    key_response = client.post(
        "/get_pub_cert",
        json={"sid": "PRD001"},
    )

    assert key_response.status_code == 200

    key_data = key_response.get_json()
    public_key_pem = base64.b64decode(key_data["public_key_pem_b64"])
    public_key = load_public_key_pem(public_key_pem)

    aes_key = os.urandom(32)
    iv = os.urandom(16)
    enc_key = rsa_oaep_encrypt(public_key, aes_key)

    response = client.post(
        "/consume",
        json={
            "sid": key_data["sid"],
            "kid": key_data["kid"],
            "enc_key_b64": base64.b64encode(enc_key).decode("ascii"),
            "iv_b64": base64.b64encode(iv).decode("ascii"),
            "ciphertext_b64": base64.b64encode(b"broken").decode("ascii"),
        },
    )

    assert response.status_code == 400

    data = response.get_json()
    assert "error" in data


def test_consume_returns_encrypted_reply(client):
    key_response = client.post(
        "/get_pub_cert",
        json={"sid": "PRD001"},
    )

    assert key_response.status_code == 200

    key_data = key_response.get_json()
    sid = key_data["sid"]
    kid = key_data["kid"]

    server_public_key_pem = base64.b64decode(key_data["public_key_pem_b64"])
    server_public_key = load_public_key_pem(server_public_key_pem)

    plaintext = b'{"request":"ping"}'

    aes_key = os.urandom(32)
    iv = os.urandom(16)

    ciphertext = aes_cbc_encrypt(aes_key, iv, plaintext)
    enc_key = rsa_oaep_encrypt(server_public_key, aes_key)

    external_private_key = generate_rsa_keypair()
    external_public_key_pem = serialize_public_key_pem(external_private_key)

    response = client.post(
        "/consume",
        json={
            "sid": sid,
            "kid": kid,
            "enc_key_b64": base64.b64encode(enc_key).decode("ascii"),
            "iv_b64": base64.b64encode(iv).decode("ascii"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
            "reply_public_key_pem_b64": base64.b64encode(external_public_key_pem).decode("ascii"),
        },
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ok"
    assert "reply" in data

    reply = data["reply"]
    assert "enc_key_b64" in reply
    assert "iv_b64" in reply
    assert "ciphertext_b64" in reply
    assert "hmac_b64" not in reply

    reply_enc_key = base64.b64decode(reply["enc_key_b64"])
    reply_iv = base64.b64decode(reply["iv_b64"])
    reply_ciphertext = base64.b64decode(reply["ciphertext_b64"])

    reply_aes_key = rsa_oaep_decrypt(external_private_key, reply_enc_key)

    reply_plaintext = aes_cbc_decrypt(
        reply_aes_key,
        reply_iv,
        reply_ciphertext,
    )

    assert reply_plaintext == plaintext