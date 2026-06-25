import base64
import json
import os

import pytest

import core.config as config
import core.database as database
import encrypt_service
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
import tempfile


@pytest.fixture
def client(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        monkeypatch.setattr(config, "DB_PATH", db_path)
        monkeypatch.setattr(database, "DB_PATH", db_path)

        app = encrypt_service.create_app()
        app.config.update(TESTING=True)

        with app.test_client() as test_client:
            yield test_client


def _get_server_cert(client, sid="PRD001"):
    resp = client.post("/get_pub_cert", json={"sid": sid})
    assert resp.status_code == 200
    data = resp.get_json()
    cert_pem = base64.b64decode(data["public_cert_pem_b64"])
    return data["sid"], data["kid"], cert_pem


def _cms_encrypt_payload(plaintext: bytes, server_cert_pem: bytes) -> dict:
    aes_key = os.urandom(32)
    iv = os.urandom(16)
    ciphertext = aes_cbc_encrypt(aes_key, iv, plaintext)
    enveloped_der = cms_encrypt_with_cert(aes_key, server_cert_pem)
    return {
        "enc_key_b64": base64.b64encode(enveloped_der).decode("ascii"),
        "iv_b64": base64.b64encode(iv).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    }


def _make_sap_cert() -> tuple[bytes, bytes]:
    """Return (cert_pem, private_key_pem) for the SAP reply keypair."""
    key = generate_rsa_keypair()
    cert = generate_self_signed_certificate(key)
    return serialize_certificate_pem(cert), serialize_private_key_pem(key)


def test_consume_dispatches_encrypt(client):
    sid, kid, server_cert_pem = _get_server_cert(client)

    plaintext = json.dumps(
        {
            "target": "/encrypt",
            "payload": {
                "data_b64": base64.b64encode(b"hello ksef").decode("ascii"),
                "cert_b64": base64.b64encode(server_cert_pem).decode("ascii"),
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")

    body = {"sid": sid, "kid": kid, **_cms_encrypt_payload(plaintext, server_cert_pem)}

    response = client.post("/consume", json=body)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"

    result = json.loads(base64.b64decode(data["plaintext_b64"]))
    assert result["status"] == "ok"
    assert "encrypted_b64" in result


def test_consume_rejects_missing_fields(client):
    response = client.post("/consume", json={"sid": "PRD001"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_consume_rejects_invalid_ciphertext(client):
    sid, kid, server_cert_pem = _get_server_cert(client)

    aes_key = os.urandom(32)
    iv = os.urandom(16)
    enveloped_der = cms_encrypt_with_cert(aes_key, server_cert_pem)

    response = client.post(
        "/consume",
        json={
            "sid": sid,
            "kid": kid,
            "enc_key_b64": base64.b64encode(enveloped_der).decode("ascii"),
            "iv_b64": base64.b64encode(iv).decode("ascii"),
            "ciphertext_b64": base64.b64encode(b"broken").decode("ascii"),
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_consume_returns_encrypted_reply(client):
    sid, kid, server_cert_pem = _get_server_cert(client)

    plaintext = json.dumps(
        {
            "target": "/encrypt",
            "payload": {
                "data_b64": base64.b64encode(b"roundtrip test").decode("ascii"),
                "cert_b64": base64.b64encode(server_cert_pem).decode("ascii"),
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")

    sap_cert_pem, sap_private_key_pem = _make_sap_cert()

    body = {
        "sid": sid,
        "kid": kid,
        **_cms_encrypt_payload(plaintext, server_cert_pem),
        "reply_cert_pem_b64": base64.b64encode(sap_cert_pem).decode("ascii"),
    }

    response = client.post("/consume", json=body)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "reply" in data

    reply = data["reply"]
    assert "enc_key_b64" in reply
    assert "iv_b64" in reply
    assert "ciphertext_b64" in reply
    assert "hmac_b64" not in reply

    enveloped_der = base64.b64decode(reply["enc_key_b64"])
    reply_iv = base64.b64decode(reply["iv_b64"])
    reply_ciphertext = base64.b64decode(reply["ciphertext_b64"])

    reply_aes_key = cms_decrypt_with_key(enveloped_der, sap_cert_pem, sap_private_key_pem)

    reply_plaintext = aes_cbc_decrypt(reply_aes_key, reply_iv, reply_ciphertext)
    result = json.loads(reply_plaintext.decode("utf-8"))

    assert result["status"] == "ok"
    assert "encrypted_b64" in result


def test_consume_rejects_unknown_target(client):
    sid, kid, server_cert_pem = _get_server_cert(client)

    plaintext = json.dumps(
        {"target": "/nonexistent", "payload": {}},
        separators=(",", ":"),
    ).encode("utf-8")

    body = {"sid": sid, "kid": kid, **_cms_encrypt_payload(plaintext, server_cert_pem)}

    response = client.post("/consume", json=body)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "nonexistent" in data["error"]


def test_consume_rejects_invalid_json_plaintext(client):
    sid, kid, server_cert_pem = _get_server_cert(client)

    plaintext = b"this is not json"

    body = {"sid": sid, "kid": kid, **_cms_encrypt_payload(plaintext, server_cert_pem)}

    response = client.post("/consume", json=body)

    assert response.status_code == 400
    assert "error" in response.get_json()
