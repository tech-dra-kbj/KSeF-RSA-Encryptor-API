import base64

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding


def load_ksef_public_key_from_string(cert_str: str):
    cert_str = cert_str.strip()

    try:
        cert_der = base64.b64decode(cert_str)
        cert = x509.load_der_x509_certificate(cert_der, default_backend())
        return cert.public_key()
    except Exception:
        pass

    try:
        cert = x509.load_pem_x509_certificate(
            cert_str.encode("utf-8"),
            default_backend(),
        )
        return cert.public_key()
    except Exception as e:
        raise ValueError(f"Błąd wczytywania certyfikatu: {e}")


def encrypt_rsa_oaep(public_key, data: bytes) -> bytes:
    return public_key.encrypt(
        data,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )