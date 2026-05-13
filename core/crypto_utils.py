import datetime
import hmac as py_hmac
import os
import subprocess
import tempfile

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.x509.oid import NameOID

from core.config import RSA_KEY_SIZE


def generate_rsa_keypair():
    """
    Generate a new RSA private key.
    """
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=RSA_KEY_SIZE,
        backend=default_backend(),
    )


def generate_self_signed_certificate(private_key) -> x509.Certificate:
    """
    Generate self-signed X509 certificate for RSA keypair.
    """
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PL"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "KSeF Encrypt Service"),
            x509.NameAttribute(NameOID.COMMON_NAME, "KSeF RSA Encryptor"),
        ]
    )

    now = datetime.datetime.now(datetime.UTC)

    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )


def serialize_certificate_pem(certificate: x509.Certificate) -> bytes:
    """
    Serialize X509 certificate to PEM.
    """
    return certificate.public_bytes(
        encoding=serialization.Encoding.PEM,
    )


def load_certificate_pem(cert_pem: bytes) -> x509.Certificate:
    """
    Load X509 certificate from PEM.
    """
    return x509.load_pem_x509_certificate(cert_pem)


def serialize_private_key_pem(private_key) -> bytes:
    """
    Serialize private key to PEM format.
    """
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def serialize_public_key_pem(private_key) -> bytes:
    """
    Extract and serialize public key to PEM format.
    """
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_private_key_pem(private_key_pem: bytes, password: bytes | None = None):
    """
    Load private key from PEM bytes.
    """
    return serialization.load_pem_private_key(
        private_key_pem,
        password=password,
    )


def load_public_key_pem(public_key_pem: bytes):
    """
    Load public key from PEM bytes.
    """
    return serialization.load_pem_public_key(public_key_pem)


def _run_openssl(command: list[str]) -> None:
    """
    Run OpenSSL command and raise readable error on failure.
    """
    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
    )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        message = stderr or stdout or "OpenSSL command failed."
        raise RuntimeError(message)


def cms_encrypt_with_cert(data: bytes, certificate_pem: bytes) -> bytes:
    """
    Encrypt data using CMS/PKCS7 envelope.

    Output format: DER.
    Intended to be compatible with SAP SSFW_KRN_ENVELOPE.
    """
    cert_path = None
    input_path = None
    output_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False) as cert_file:
            cert_file.write(certificate_pem)
            cert_path = cert_file.name

        with tempfile.NamedTemporaryFile(delete=False) as input_file:
            input_file.write(data)
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(delete=False) as output_file:
            output_path = output_file.name

        _run_openssl(
            [
                "openssl",
                "cms",
                "-encrypt",
                "-binary",
                "-outform",
                "DER",
                "-aes256",
                "-in",
                input_path,
                "-out",
                output_path,
                cert_path,
            ]
        )

        with open(output_path, "rb") as output_file:
            return output_file.read()

    finally:
        for path in (cert_path, input_path, output_path):
            if path and os.path.exists(path):
                os.unlink(path)


def cms_decrypt_with_key(
    enveloped_der: bytes,
    certificate_pem: bytes,
    private_key_pem: bytes,
) -> bytes:
    """
    Decrypt CMS/PKCS7 envelope.

    Input format: DER.
    Intended to be compatible with SAP SSFW_KRN_DEVELOPE.
    """
    cert_path = None
    key_path = None
    input_path = None
    output_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False) as cert_file:
            cert_file.write(certificate_pem)
            cert_path = cert_file.name

        with tempfile.NamedTemporaryFile(delete=False) as key_file:
            key_file.write(private_key_pem)
            key_path = key_file.name

        with tempfile.NamedTemporaryFile(delete=False) as input_file:
            input_file.write(enveloped_der)
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(delete=False) as output_file:
            output_path = output_file.name

        _run_openssl(
            [
                "openssl",
                "cms",
                "-decrypt",
                "-binary",
                "-inform",
                "DER",
                "-in",
                input_path,
                "-recip",
                cert_path,
                "-inkey",
                key_path,
                "-out",
                output_path,
            ]
        )

        with open(output_path, "rb") as output_file:
            return output_file.read()

    finally:
        for path in (cert_path, key_path, input_path, output_path):
            if path and os.path.exists(path):
                os.unlink(path)


def rsa_oaep_encrypt(public_key, data: bytes) -> bytes:
    """
    Encrypt data with RSA-OAEP SHA-256.

    Kept for legacy/internal tests. SAP flow should use CMS envelope.
    """
    return public_key.encrypt(
        data,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def rsa_oaep_decrypt(private_key, ciphertext: bytes) -> bytes:
    """
    Decrypt data with RSA-OAEP SHA-256.

    Kept for legacy/internal tests. SAP flow should use CMS envelope.
    """
    return private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    """
    Apply PKCS7 padding.
    """
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def pkcs7_unpad(padded: bytes, block_size: int = 16) -> bytes:
    """
    Remove PKCS7 padding.
    """
    if not padded or len(padded) % block_size != 0:
        raise ValueError("Invalid padded data length.")

    pad_len = padded[-1]

    if pad_len < 1 or pad_len > block_size:
        raise ValueError("Invalid PKCS7 padding length.")

    if padded[-pad_len:] != bytes([pad_len]) * pad_len:
        raise ValueError("Invalid PKCS7 padding bytes.")

    return padded[:-pad_len]


def aes_cbc_encrypt(aes_key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    """
    Encrypt plaintext with AES-CBC and PKCS7 padding.
    """
    if len(iv) != 16:
        raise ValueError("IV must be 16 bytes.")

    if len(aes_key) not in (16, 24, 32):
        raise ValueError("AES key must be 16, 24 or 32 bytes.")

    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CBC(iv),
    )
    encryptor = cipher.encryptor()
    padded = pkcs7_pad(plaintext)

    return encryptor.update(padded) + encryptor.finalize()


def aes_cbc_decrypt(aes_key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """
    Decrypt ciphertext with AES-CBC and PKCS7 unpadding.
    """
    if len(iv) != 16:
        raise ValueError("IV must be 16 bytes.")

    if len(aes_key) not in (16, 24, 32):
        raise ValueError("AES key must be 16, 24 or 32 bytes.")

    if len(ciphertext) % 16 != 0:
        raise ValueError("Ciphertext length must be a multiple of 16.")

    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CBC(iv),
    )
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    return pkcs7_unpad(padded)


def compute_hmac_sha256(key: bytes, data: bytes) -> bytes:
    """
    Compute HMAC-SHA256.

    Kept for compatibility with old tests/tools.
    """
    h = hmac.HMAC(key, hashes.SHA256())
    h.update(data)
    return h.finalize()


def verify_hmac_sha256(key: bytes, data: bytes, expected_mac: bytes) -> None:
    """
    Verify HMAC-SHA256.

    Kept for compatibility with old tests/tools.
    """
    actual_mac = compute_hmac_sha256(key, data)

    if not py_hmac.compare_digest(actual_mac, expected_mac):
        raise ValueError("HMAC verification failed.")