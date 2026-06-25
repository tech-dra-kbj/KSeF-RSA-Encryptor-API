import base64
import time
import uuid

from core.config import CLEANUP_GRACE_SECONDS, KEY_TTL_SECONDS, SID_REGEX
from core.crypto_utils import (
    generate_rsa_keypair,
    generate_self_signed_certificate,
    serialize_certificate_pem,
    serialize_private_key_pem,
    serialize_public_key_pem,
)
from core.database import get_connection, transaction_immediate


def validate_sid(sid: str):
    """
    Validate SID format.
    Must match exactly 6 uppercase alphanumeric characters.
    """
    if not sid or not SID_REGEX.match(sid):
        raise ValueError("Invalid SID format. Expected 6 uppercase alphanumeric characters.")


def cleanup_expired(now: int):
    """
    Remove expired keys from database.
    Small grace period prevents race conditions at boundary.
    """
    cutoff = now - CLEANUP_GRACE_SECONDS

    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM keys WHERE expires_at < ?;",
            (cutoff,),
        )
    finally:
        conn.close()


def get_or_create_key(sid: str) -> dict:
    """
    Return an active RSA key/certificate for given SID.
    If no valid key exists, generate and store a new one.
    """
    validate_sid(sid)

    now = int(time.time())

    cleanup_expired(now)

    with transaction_immediate() as conn:
        row = conn.execute(
            """
            SELECT
                sid,
                kid,
                public_key_pem,
                public_cert_pem,
                created_at,
                expires_at
            FROM keys
            WHERE sid = ?
            AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1;
            """,
            (sid, now),
        ).fetchone()

        if row:
            return {
                "sid": row["sid"],
                "kid": row["kid"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "public_key_pem_b64": base64.b64encode(
                    row["public_key_pem"]
                ).decode("ascii"),
                "public_cert_pem_b64": base64.b64encode(
                    row["public_cert_pem"]
                ).decode("ascii"),
            }

        private_key = generate_rsa_keypair()
        certificate = generate_self_signed_certificate(private_key)

        private_pem = serialize_private_key_pem(private_key)
        public_pem = serialize_public_key_pem(private_key)
        public_cert_pem = serialize_certificate_pem(certificate)

        kid = str(uuid.uuid4())
        created_at = now
        expires_at = now + KEY_TTL_SECONDS

        conn.execute(
            """
            INSERT INTO keys (
                sid,
                kid,
                private_key_pem,
                public_key_pem,
                public_cert_pem,
                created_at,
                expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                sid,
                kid,
                private_pem,
                public_pem,
                public_cert_pem,
                created_at,
                expires_at,
            ),
        )

        return {
            "sid": sid,
            "kid": kid,
            "created_at": created_at,
            "expires_at": expires_at,
            "public_key_pem_b64": base64.b64encode(public_pem).decode("ascii"),
            "public_cert_pem_b64": base64.b64encode(public_cert_pem).decode("ascii"),
        }


def get_private_key_pem_for_kid(sid: str, kid: str) -> bytes:
    """
    Fetch private key PEM for given SID/KID if key is still active.
    """
    validate_sid(sid)

    if not kid:
        raise ValueError("Missing 'kid'.")

    now = int(time.time())

    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT private_key_pem
            FROM keys
            WHERE sid = ?
            AND kid = ?
            AND expires_at > ?
            LIMIT 1;
            """,
            (sid, kid, now),
        ).fetchone()

        if not row:
            raise ValueError("Key not found or expired for given sid/kid.")

        return row["private_key_pem"]
    finally:
        conn.close()


def get_certificate_pem_for_kid(sid: str, kid: str) -> bytes:
    """
    Fetch public certificate PEM for given SID/KID if key is still active.
    """
    validate_sid(sid)

    if not kid:
        raise ValueError("Missing 'kid'.")

    now = int(time.time())

    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT public_cert_pem
            FROM keys
            WHERE sid = ?
            AND kid = ?
            AND expires_at > ?
            LIMIT 1;
            """,
            (sid, kid, now),
        ).fetchone()

        if not row:
            raise ValueError("Certificate not found or expired for given sid/kid.")

        return row["public_cert_pem"]
    finally:
        conn.close()