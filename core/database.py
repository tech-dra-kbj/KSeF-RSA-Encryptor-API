import os
import sqlite3
from contextlib import contextmanager

from core.config import DB_PATH


def ensure_instance_dir():
    """
    Ensure that the directory for the SQLite database exists.
    """
    instance_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir, exist_ok=True)


def get_connection():
    """
    Create and return a new SQLite connection.

    Each request should use its own connection.
    isolation_level=None allows manual transaction control.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a SQLite table.
    """
    rows = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
    return any(row["name"] == column_name for row in rows)


def _migrate_schema(conn):
    """
    Apply lightweight schema migrations.
    """
    if not _column_exists(conn, "keys", "public_cert_pem"):
        conn.execute("""
        ALTER TABLE keys
        ADD COLUMN public_cert_pem BLOB;
        """)


def init_db():
    """
    Initialize the database:
    - Ensure directory exists
    - Enable WAL mode
    - Create required tables and indexes
    - Apply lightweight migrations
    """
    ensure_instance_dir()

    conn = get_connection()
    try:
        # Enable Write-Ahead Logging for better multi-process concurrency
        conn.execute("PRAGMA journal_mode=WAL;")

        # Balance between durability and performance
        conn.execute("PRAGMA synchronous=NORMAL;")

        # Enable foreign key constraints (future-proofing)
        conn.execute("PRAGMA foreign_keys=ON;")

        # Create keys table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            sid TEXT NOT NULL,
            kid TEXT NOT NULL,
            private_key_pem BLOB NOT NULL,
            public_key_pem BLOB NOT NULL,
            public_cert_pem BLOB,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            PRIMARY KEY (sid, kid)
        );
        """)

        _migrate_schema(conn)

        # Index for faster lookups by SID
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_keys_sid
        ON keys(sid);
        """)

        # Index for cleanup queries
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_keys_expires
        ON keys(expires_at);
        """)

    finally:
        conn.close()


@contextmanager
def transaction_immediate():
    """
    Context manager for a BEGIN IMMEDIATE transaction.

    BEGIN IMMEDIATE prevents concurrent writers from generating
    multiple keys for the same SID at the same time.
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.close()