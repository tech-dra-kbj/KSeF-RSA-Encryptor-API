import hmac as py_hmac

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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


def rsa_oaep_encrypt(public_key, data: bytes) -> bytes:
    """
    Encrypt data with RSA-OAEP SHA-256.
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
    """
    h = hmac.HMAC(key, hashes.SHA256())
    h.update(data)
    return h.finalize()


def verify_hmac_sha256(key: bytes, data: bytes, expected_mac: bytes) -> None:
    """
    Verify HMAC-SHA256.
    """
    actual_mac = compute_hmac_sha256(key, data)

    if not py_hmac.compare_digest(actual_mac, expected_mac):
        raise ValueError("HMAC verification failed.")