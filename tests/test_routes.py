import os
import tempfile

import pytest

import core.config as config
import core.database as database
import encrypt_service


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


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "KSeF RSA Encryptor"


def test_index(client):
    response = client.get("/")

    assert response.status_code == 200

    data = response.get_json()
    assert data["service"] == "KSeF RSA Encryptor 1.2.0"
    assert data["docs"] == "/apidocs"
    assert data["health"] == "/health"
    assert data["generate_pdf"] == "/generatePDF"


def test_get_pub_cert_success(client):
    response = client.post(
        "/get_pub_cert",
        json={"sid": "PRD001"},
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["sid"] == "PRD001"
    assert isinstance(data["kid"], str)
    assert isinstance(data["created_at"], int)
    assert isinstance(data["expires_at"], int)
    assert data["expires_at"] > data["created_at"]
    assert isinstance(data["public_key_pem_b64"], str)


def test_get_pub_cert_reuses_active_key(client):
    first_response = client.post(
        "/get_pub_cert",
        json={"sid": "PRD001"},
    )
    second_response = client.post(
        "/get_pub_cert",
        json={"sid": "PRD001"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first = first_response.get_json()
    second = second_response.get_json()

    assert first["kid"] == second["kid"]
    assert first["public_key_pem_b64"] == second["public_key_pem_b64"]


def test_get_pub_cert_missing_sid(client):
    response = client.post(
        "/get_pub_cert",
        json={},
    )

    assert response.status_code == 400

    data = response.get_json()
    assert "error" in data


def test_get_pub_cert_invalid_sid(client):
    response = client.post(
        "/get_pub_cert",
        json={"sid": "prd001"},
    )

    assert response.status_code == 400

    data = response.get_json()
    assert "error" in data