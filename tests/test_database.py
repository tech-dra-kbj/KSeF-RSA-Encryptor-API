import os
import sqlite3
import tempfile

import pytest

import core.database as database
import core.config as config


@pytest.fixture
def temp_db_path(monkeypatch):
    """
    Provide a temporary SQLite DB path and patch config.DB_PATH.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        monkeypatch.setattr(config, "DB_PATH", db_path)
        monkeypatch.setattr(database, "DB_PATH", db_path)
        yield db_path


def test_init_db_creates_file_and_table(temp_db_path):
    database.init_db()

    assert os.path.exists(temp_db_path)

    conn = sqlite3.connect(temp_db_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='keys';"
        )
        row = cursor.fetchone()
        assert row is not None
    finally:
        conn.close()


def test_insert_and_select_key(temp_db_path):
    database.init_db()

    conn = database.get_connection()
    try:
        conn.execute(
            """
            INSERT INTO keys (sid, kid, private_key_pem, public_key_pem, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("PRD001", "kid1", b"priv", b"pub", 1000, 2000),
        )

        row = conn.execute(
            "SELECT sid, kid FROM keys WHERE sid = ?",
            ("PRD001",),
        ).fetchone()

        assert row is not None
        assert row["sid"] == "PRD001"
        assert row["kid"] == "kid1"

    finally:
        conn.close()


def test_transaction_immediate(temp_db_path):
    database.init_db()

    with database.transaction_immediate() as conn:
        conn.execute(
            """
            INSERT INTO keys (sid, kid, private_key_pem, public_key_pem, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("PRD002", "kid2", b"priv", b"pub", 1000, 2000),
        )

    # Verify commit happened
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT sid FROM keys WHERE sid = ?",
            ("PRD002",),
        ).fetchone()

        assert row is not None
    finally:
        conn.close()