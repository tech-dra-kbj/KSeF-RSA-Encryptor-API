from flask import Flask, Response, request
from flasgger import Swagger
from flask_cors import CORS
import base64
import os
import json
from cryptography.hazmat.primitives.asymmetric import rsa, ec, utils
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import logging
from lxml import etree
from signxml.xades import XAdESSigner
from signxml import methods
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding
from urllib.parse import urlparse, urlunparse
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives import hashes

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
            body = {"status": "error", "code": 101, "message": "Brak wymaganych pól"}
            return Response(json.dumps(body, separators=(",", ":")), status=400, mimetype="application/json")

        try:
            data = base64.b64decode(data_b64)
        except Exception as e:
            body = {"status": "error", "code": 102, "message": f"Błąd Base64: {e}"}
            return Response(json.dumps(body, separators=(",", ":")), status=400, mimetype="application/json")

        try:
            public_key = load_ksef_public_key_from_string(cert_b64)
        except Exception as e:
            body = {"status": "error", "code": 103, "message": str(e)}
            return Response(json.dumps(body, separators=(",", ":")), status=400, mimetype="application/json")

        try:
            encrypted = encrypt_rsa_oaep(public_key, data)
        except Exception as e:
            body = {"status": "error", "code": 104, "message": f"Błąd szyfrowania: {e}"}
            return Response(json.dumps(body, separators=(",", ":")), status=500, mimetype="application/json")

        encrypted_b64 = base64.b64encode(encrypted).decode("ascii")
        body = {"status": "ok", "encrypted_b64": encrypted_b64}
        return Response(json.dumps(body, separators=(",", ":")), mimetype="application/json")

    except Exception as e:
        body = {"status": "error", "code": 199, "message": f"Nieoczekiwany błąd: {e}"}
        return Response(json.dumps(body, separators=(",", ":")), status=500, mimetype="application/json")

@app.route("/sign_xml", methods=["POST"])
def sign_xml():
    try:
        body = request.get_json(force=True, silent=False)

        # Wymagane pola (wszystko w Base64)
        xml_b64 = body.get("xml_b64")
        cert_pem_b64 = body.get("cert_pem_b64")
        key_pem_b64 = body.get("key_pem_b64")

        # Opcjonalnie: hasło też w Base64 (UTF-8 po dekodowaniu)
        key_password_b64 = body.get("key_password_b64")

        # Wybór algorytmu: rsa_sha256 | ecdsa_sha256
        alg = (body.get("alg") or "rsa_sha256").lower()

        if not xml_b64 or not cert_pem_b64 or not key_pem_b64:
            return Response(
                json.dumps({"error": "Wymagane: 'xml_b64', 'cert_pem_b64', 'key_pem_b64'."}),
                status=400,
                mimetype="application/json",
            )

        # 1) Dekoduj XML
        try:
            xml_bytes = base64.b64decode(xml_b64)
        except Exception as e:
            return Response(
                json.dumps({"error": f"Błąd Base64 w xml_b64: {e}"}),
                status=400,
                mimetype="application/json",
            )

        # 2) Dekoduj cert PEM
        try:
            cert_pem_bytes = base64.b64decode(cert_pem_b64)
            cert_obj = x509.load_pem_x509_certificate(cert_pem_bytes)
            cert_pem_str = cert_obj.public_bytes(Encoding.PEM).decode("utf-8")
        except Exception as e:
            return Response(
                json.dumps({"error": f"Nie można wczytać certyfikatu PEM (cert_pem_b64): {e}"}),
                status=400,
                mimetype="application/json",
            )

        # 3) Dekoduj hasło (opcjonalnie)
        password_bytes = None
        if key_password_b64:
            try:
                password_bytes = base64.b64decode(key_password_b64)
            except Exception as e:
                return Response(
                    json.dumps({"error": f"Błąd Base64 w key_password_b64: {e}"}),
                    status=400,
                    mimetype="application/json",
                )

        # 4) Wczytaj klucz prywatny
        try:
            key_pem_bytes = base64.b64decode(key_pem_b64)
            key = load_pem_private_key(
                key_pem_bytes,
                password=password_bytes,
            )
        except Exception as e:
            return Response(
                json.dumps({"error": f"Nie można wczytać klucza prywatnego PEM (key_pem_b64): {e}"}),
                status=400,
                mimetype="application/json",
            )

        # 5) Walidacja: cert pasuje do klucza (public key match)
        try:
            cert_pub = cert_obj.public_key()
            key_pub = key.public_key()
            if cert_pub.public_numbers() != key_pub.public_numbers():
                return Response(
                    json.dumps({"error": "Certyfikat nie pasuje do klucza prywatnego (public key mismatch)."}),
                    status=400,
                    mimetype="application/json",
                )
        except Exception as e:
            return Response(
                json.dumps({"error": f"Nie można porównać kluczy (cert/key): {e}"}),
                status=400,
                mimetype="application/json",
            )

        # 6) Dobór algorytmu podpisu XMLDSig/XAdES + walidacja typu klucza
        if alg == "rsa_sha256":
            if not isinstance(key, rsa.RSAPrivateKey):
                return Response(
                    json.dumps({"error": "Wybrano rsa_sha256, ale klucz prywatny nie jest RSA."}),
                    status=400,
                    mimetype="application/json",
                )
            signature_algorithm = "rsa-sha256"

        elif alg == "ecdsa_sha256":
            if not isinstance(key, ec.EllipticCurvePrivateKey):
                return Response(
                    json.dumps({"error": "Wybrano ecdsa_sha256, ale klucz prywatny nie jest EC/ECDSA."}),
                    status=400,
                    mimetype="application/json",
                )
            # Jeśli chcesz wymusić P-256 (KSeF typowo tak):
            if not isinstance(key.curve, ec.SECP256R1):
                return Response(
                    json.dumps({"error": f"Klucz EC nie jest P-256 (secp256r1). Jest: {type(key.curve).__name__}"}),
                    status=400,
                    mimetype="application/json",
                )
            signature_algorithm = "ecdsa-sha256"

        else:
            return Response(
                json.dumps({"error": "alg musi być 'rsa_sha256' albo 'ecdsa_sha256'."}),
                status=400,
                mimetype="application/json",
            )

        # 7) Podpis XAdES (enveloped)
        root = etree.fromstring(xml_bytes)

        signer = XAdESSigner(
            method=methods.enveloped,
            signature_algorithm=signature_algorithm,
            c14n_algorithm="http://www.w3.org/2006/12/xml-c14n11",
        )

        # Te metody zależą od wersji signxml/xades; jeśli ich nie ma w Twojej wersji,
        # to te bloki nic nie zepsują (po prostu zostaną pominięte).
        try:
            signer.add_signing_time()
        except Exception:
            pass
        try:
            signer.add_signing_certificate(cert_pem_str)
        except Exception:
            pass

        signed_root = signer.sign(data=root, key=key, cert=cert_pem_str)
        signed_xml_bytes = etree.tostring(signed_root, xml_declaration=True, encoding="utf-8")

        return Response(
            json.dumps({
                "signed_xml_b64": base64.b64encode(signed_xml_bytes).decode("ascii"),
                "alg_used": alg,
            }),
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("XAdES signing error")
        return Response(json.dumps({"error": str(e)}), status=400, mimetype="application/json")

@app.route("/sign_link", methods=["POST"])
def sign_link():
    try:
        body = request.get_json(force=True, silent=False)

        link_b64 = body.get("link_b64")
        cert_pem_b64 = body.get("cert_pem_b64")
        key_pem_b64 = body.get("key_pem_b64")

        # ZMIANA: hasło w Base64 (UTF-8 po dekodowaniu), tak jak w /sign_xml
        key_password_b64 = body.get("key_password_b64")

        # (opcjonalnie) kompatybilność wsteczna – jeśli chcesz USUNĄĆ, skasuj ten fallback
        key_password_plain = body.get("key_password")

        alg = (body.get("alg") or "rsa_pss").lower()                 # rsa_pss | ecdsa_p256
        ecdsa_format = (body.get("ecdsa_format") or "p1363").lower() # p1363 | der

        if not link_b64 or not cert_pem_b64 or not key_pem_b64:
            return Response(
                json.dumps({"error": "Wymagane: 'link_b64', 'cert_pem_b64', 'key_pem_b64'."}),
                status=400, mimetype="application/json",
            )

        # 0) Hasło -> bytes (Base64), spójnie z /sign_xml
        password_bytes = None
        if key_password_b64:
            try:
                password_bytes = base64.b64decode(key_password_b64)
            except Exception as e:
                return Response(
                    json.dumps({"error": f"Błąd Base64 w key_password_b64: {e}"}),
                    status=400,
                    mimetype="application/json",
                )
        elif key_password_plain:
            # (opcjonalnie) fallback – usuń, jeśli chcesz wymusić wyłącznie Base64
            password_bytes = key_password_plain.encode("utf-8")

        # 1) Dekoduj link i sparsuj URL
        link_str = base64.b64decode(link_b64).decode("utf-8").strip()
        link_str = link_str.rstrip("/")

        parse_input = link_str
        if "://" not in parse_input:
            parse_input = "https://" + parse_input

        parsed = urlparse(parse_input)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc
        path = parsed.path

        if not netloc or not path:
            return Response(
                json.dumps({"error": "Nieprawidłowy URL w link_b64 (brak host/path)."}),
                status=400,
                mimetype="application/json",
            )

        # 2) Segmenty ścieżki: 6 segmentów bez podpisu
        segments = [seg for seg in path.strip("/").split("/") if seg]
        if len(segments) < 6:
            return Response(
                json.dumps({"error": "Za mało segmentów w ścieżce (min. 6: certificate/.../invoiceHash)."}),
                status=400,
                mimetype="application/json",
            )

        core_segs = segments[:6]

        # 3) Ciąg do podpisu: host + "/" + core segmenty
        string_to_sign = f"{netloc}/" + "/".join(core_segs)
        data_to_sign = string_to_sign.encode("utf-8")

        # 4) Wczytaj cert i klucz prywatny
        try:
            cert_pem_bytes = base64.b64decode(cert_pem_b64)
            cert_obj = x509.load_pem_x509_certificate(cert_pem_bytes)
        except Exception as e:
            return Response(json.dumps({"error": f"Nie można wczytać certyfikatu PEM: {e}"}),
                            status=400, mimetype="application/json")

        try:
            key_pem_bytes = base64.b64decode(key_pem_b64)
            private_key = load_pem_private_key(
                key_pem_bytes,
                password=password_bytes,   # <-- ZMIANA: password_bytes zamiast encode(utf-8)
            )
        except Exception as e:
            return Response(json.dumps({"error": f"Nie można wczytać klucza prywatnego PEM: {e}"}),
                            status=400, mimetype="application/json")

        # 5) Walidacja: cert pasuje do private key
        cert_pub = cert_obj.public_key()
        key_pub = private_key.public_key()
        try:
            if cert_pub.public_numbers() != key_pub.public_numbers():
                return Response(json.dumps({"error": "Certyfikat nie pasuje do klucza prywatnego (public key mismatch)."}),
                                status=400, mimetype="application/json")
        except Exception as e:
            return Response(json.dumps({"error": f"Nie można porównać kluczy (cert/key): {e}"}),
                            status=400, mimetype="application/json")

        # 6) Podpis – wybór algorytmu
        if alg == "rsa_pss":
            if not isinstance(private_key, rsa.RSAPrivateKey):
                return Response(json.dumps({"error": "Wybrano rsa_pss, ale klucz prywatny nie jest RSA."}),
                                status=400, mimetype="application/json")
            if private_key.key_size < 2048:
                return Response(json.dumps({"error": f"Za krótki klucz RSA: {private_key.key_size} (min. 2048)."}),
                                status=400, mimetype="application/json")

            signature_bytes = private_key.sign(
                data_to_sign,
                asym_padding.PSS(
                    mgf=asym_padding.MGF1(hashes.SHA256()),
                    salt_length=32,
                ),
                hashes.SHA256(),
            )

        elif alg == "ecdsa_p256":
            if not isinstance(private_key, ec.EllipticCurvePrivateKey):
                return Response(json.dumps({"error": "Wybrano ecdsa_p256, ale klucz prywatny nie jest EC/ECDSA."}),
                                status=400, mimetype="application/json")
            if not isinstance(private_key.curve, ec.SECP256R1):
                return Response(json.dumps({"error": f"Klucz EC nie jest P-256 (secp256r1). Jest: {type(private_key.curve).__name__}"}),
                                status=400, mimetype="application/json")

            sig_der = private_key.sign(data_to_sign, ec.ECDSA(hashes.SHA256()))

            if ecdsa_format == "der":
                signature_bytes = sig_der
            elif ecdsa_format == "p1363":
                r, s = utils.decode_dss_signature(sig_der)
                signature_bytes = r.to_bytes(32, "big") + s.to_bytes(32, "big")
            else:
                return Response(json.dumps({"error": "ecdsa_format musi być 'p1363' albo 'der'."}),
                                status=400, mimetype="application/json")
        else:
            return Response(json.dumps({"error": "alg musi być 'rsa_pss' albo 'ecdsa_p256'."}),
                            status=400, mimetype="application/json")

        # 7) Base64URL podpisu (bez '=')
        sig_b64url = base64.urlsafe_b64encode(signature_bytes).decode("ascii").rstrip("=")

        # 8) Finalny URL: core + podpis
        new_path = "/" + "/".join(core_segs + [sig_b64url])
        final_url = urlunparse((scheme, netloc, new_path, "", "", ""))

        return Response(
            json.dumps({
                "link_b64": base64.b64encode(final_url.encode("utf-8")).decode("ascii"),
                "alg_used": alg,
                "ecdsa_format_used": (ecdsa_format if alg == "ecdsa_p256" else None),
            }),
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("sign_link error")
        return Response(json.dumps({"error": str(e)}), status=400, mimetype="application/json")

@app.route("/health", methods=["GET"])
def health():
    body = {"status": "ok", "service": "KSeF RSA Encryptor"}
    return Response(json.dumps(body, separators=(",", ":")), mimetype="application/json")


@app.route("/", methods=["GET"])
def index():
    body = {
        "service": "KSeF RSA Encryptor 1.1.0",
        "docs": "/apidocs",
        "health": "/health"
    }
    return Response(json.dumps(body, separators=(",", ":")), mimetype="application/json")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
