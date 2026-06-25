import base64
import os
import tempfile

import pytest
from cryptography.hazmat.primitives import serialization

import core.config as config
import core.database as database
import core.key_manager as key_manager


@pytest.fixture
def temp_db_path(monkeypatch):
    """
    Provide a temporary SQLite DB path and patch all modules that keep DB_PATH.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        monkeypatch.setattr(config, "DB_PATH", db_path)
        monkeypatch.setattr(database, "DB_PATH", db_path)

        database.init_db()
        yield db_path


def test_validate_sid_valid():
    key_manager.validate_sid("PRD001")


def test_validate_sid_invalid():
    invalid_sids = ["prd001", "PRD01", "PRD0001", "PRD-01", "", None]

    for sid in invalid_sids:
        with pytest.raises(ValueError):
            key_manager.validate_sid(sid)


def test_get_or_create_key_creates_key(temp_db_path):
    result = key_manager.get_or_create_key("PRD001")

    assert result["sid"] == "PRD001"
    assert isinstance(result["kid"], str)
    assert isinstance(result["created_at"], int)
    assert isinstance(result["expires_at"], int)
    assert result["expires_at"] > result["created_at"]
    assert isinstance(result["public_key_pem_b64"], str)

    public_key_pem = base64.b64decode(result["public_key_pem_b64"])
    public_key = serialization.load_pem_public_key(public_key_pem)

    assert public_key.key_size == config.RSA_KEY_SIZE


def test_get_or_create_key_reuses_active_key(temp_db_path):
    first = key_manager.get_or_create_key("PRD001")
    second = key_manager.get_or_create_key("PRD001")

    assert second["sid"] == first["sid"]
    assert second["kid"] == first["kid"]
    assert second["created_at"] == first["created_at"]
    assert second["expires_at"] == first["expires_at"]
    assert second["public_key_pem_b64"] == first["public_key_pem_b64"]


def test_get_or_create_key_creates_separate_keys_per_sid(temp_db_path):
    first = key_manager.get_or_create_key("PRD001")
    second = key_manager.get_or_create_key("QAS001")

    assert first["sid"] == "PRD001"
    assert second["sid"] == "QAS001"
    assert first["kid"] != second["kid"]
    assert first["public_key_pem_b64"] != second["public_key_pem_b64"]


def test_cleanup_expired_removes_old_keys(temp_db_path):
    conn = database.get_connection()
    try:
        conn.execute(
            """
            INSERT INTO keys (sid, kid, private_key_pem, public_key_pem, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("PRD001", "expired-kid", b"priv", b"pub", 1000, 1000),
        )
    finally:
        conn.close()

    key_manager.cleanup_expired(now=2000)

    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT kid FROM keys WHERE sid = ? AND kid = ?",
            ("PRD001", "expired-kid"),
        ).fetchone()

        assert row is None
    finally:
        conn.close()


def test_expired_key_is_not_reused(temp_db_path):
    conn = database.get_connection()
    try:
        conn.execute(
            """
            INSERT INTO keys (sid, kid, private_key_pem, public_key_pem, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("PRD001", "expired-kid", b"priv", b"pub", 1000, 1000),
        )
    finally:
        conn.close()

    result = key_manager.get_or_create_key("PRD001")

    assert result["sid"] == "PRD001"
    assert result["kid"] != "expired-kid"