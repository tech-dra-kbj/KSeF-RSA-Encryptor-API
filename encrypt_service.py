from flask import Flask, jsonify, request
from flasgger import Swagger
from flask_cors import CORS
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import logging

app = Flask(__name__)
CORS(app)

swagger = Swagger(app, template_file="swaggerapi.yaml")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def load_ksef_public_key_from_string(cert_str: str):
    cert_str = cert_str.strip()
    try:
        cert_der = base64.b64decode(cert_str)
        cert = x509.load_der_x509_certificate(cert_der, default_backend())
        return cert.public_key()
    except Exception:
        pass
    try:
        cert = x509.load_pem_x509_certificate(cert_str.encode("utf-8"), default_backend())
        return cert.public_key()
    except Exception as e:
        raise ValueError(f"Błąd wczytywania certyfikatu: {e}")


def encrypt_rsa_oaep(public_key, data: bytes) -> bytes:
    return public_key.encrypt(
        data,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


@app.route("/encrypt", methods=["POST"])
def encrypt_endpoint():
    try:
        payload = request.get_json(force=True)
        data_b64 = payload.get("data_b64")
        cert_b64 = payload.get("cert_b64")
        return_b64 = payload.get("return_b64", True)

        if not data_b64 or not cert_b64:
            return jsonify({"status": "error", "code": 101, "message": "Brak wymaganych pól"}), 400

        try:
            data = base64.b64decode(data_b64)
        except Exception as e:
            return jsonify({"status": "error", "code": 102, "message": f"Błąd Base64: {e}"}), 400

        try:
            public_key = load_ksef_public_key_from_string(cert_b64)
        except Exception as e:
            return jsonify({"status": "error", "code": 103, "message": str(e)}), 400

        encrypted = encrypt_rsa_oaep(public_key, data)
        encrypted_b64 = base64.b64encode(encrypted).decode("ascii")

        return jsonify({"status": "ok", "encrypted_b64": encrypted_b64})

    except Exception as e:
        return jsonify({"status": "error", "code": 199, "message": f"Nieoczekiwany błąd: {e}"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "KSeF RSA Encryptor"})


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "KSeF RSA Encryptor",
        "docs": "/apidocs",
        "health": "/health"
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)