import base64
import json
import logging
from urllib.parse import urlparse, urlunparse

from flask import Blueprint, Response, request
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa, utils
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

bp = Blueprint("sign_link", __name__)


@bp.route("/sign_link", methods=["POST"])
def sign_link():
    try:
        body = request.get_json(force=True, silent=False)

        link_b64 = body.get("link_b64")
        cert_pem_b64 = body.get("cert_pem_b64")
        key_pem_b64 = body.get("key_pem_b64")

        key_password_b64 = body.get("key_password_b64")
        key_password_plain = body.get("key_password")

        alg = (body.get("alg") or "rsa_pss").lower()
        ecdsa_format = (body.get("ecdsa_format") or "p1363").lower()

        if not link_b64 or not cert_pem_b64 or not key_pem_b64:
            return Response(
                json.dumps({"error": "Wymagane: 'link_b64', 'cert_pem_b64', 'key_pem_b64'."}),
                status=400,
                mimetype="application/json",
            )

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
            password_bytes = key_password_plain.encode("utf-8")

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

        segments = [seg for seg in path.strip("/").split("/") if seg]
        if len(segments) < 6:
            return Response(
                json.dumps({"error": "Za mało segmentów w ścieżce (min. 6: certificate/.../invoiceHash)."}),
                status=400,
                mimetype="application/json",
            )

        core_segs = segments[:6]

        string_to_sign = f"{netloc}/" + "/".join(core_segs)
        data_to_sign = string_to_sign.encode("utf-8")

        try:
            cert_pem_bytes = base64.b64decode(cert_pem_b64)
            cert_obj = x509.load_pem_x509_certificate(cert_pem_bytes)
        except Exception as e:
            return Response(
                json.dumps({"error": f"Nie można wczytać certyfikatu PEM: {e}"}),
                status=400,
                mimetype="application/json",
            )

        try:
            key_pem_bytes = base64.b64decode(key_pem_b64)
            private_key = load_pem_private_key(
                key_pem_bytes,
                password=password_bytes,
            )
        except Exception as e:
            return Response(
                json.dumps({"error": f"Nie można wczytać klucza prywatnego PEM: {e}"}),
                status=400,
                mimetype="application/json",
            )

        cert_pub = cert_obj.public_key()
        key_pub = private_key.public_key()
        try:
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

        if alg == "rsa_pss":
            if not isinstance(private_key, rsa.RSAPrivateKey):
                return Response(
                    json.dumps({"error": "Wybrano rsa_pss, ale klucz prywatny nie jest RSA."}),
                    status=400,
                    mimetype="application/json",
                )

            if private_key.key_size < 2048:
                return Response(
                    json.dumps({"error": f"Za krótki klucz RSA: {private_key.key_size} (min. 2048)."}),
                    status=400,
                    mimetype="application/json",
                )

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
                return Response(
                    json.dumps({"error": "Wybrano ecdsa_p256, ale klucz prywatny nie jest EC/ECDSA."}),
                    status=400,
                    mimetype="application/json",
                )

            if not isinstance(private_key.curve, ec.SECP256R1):
                return Response(
                    json.dumps({"error": f"Klucz EC nie jest P-256 (secp256r1). Jest: {type(private_key.curve).__name__}"}),
                    status=400,
                    mimetype="application/json",
                )

            sig_der = private_key.sign(data_to_sign, ec.ECDSA(hashes.SHA256()))

            if ecdsa_format == "der":
                signature_bytes = sig_der
            elif ecdsa_format == "p1363":
                r, s = utils.decode_dss_signature(sig_der)
                signature_bytes = r.to_bytes(32, "big") + s.to_bytes(32, "big")
            else:
                return Response(
                    json.dumps({"error": "ecdsa_format musi być 'p1363' albo 'der'."}),
                    status=400,
                    mimetype="application/json",
                )

        else:
            return Response(
                json.dumps({"error": "alg musi być 'rsa_pss' albo 'ecdsa_p256'."}),
                status=400,
                mimetype="application/json",
            )

        sig_b64url = base64.urlsafe_b64encode(signature_bytes).decode("ascii").rstrip("=")

        new_path = "/" + "/".join(core_segs + [sig_b64url])
        final_url = urlunparse((scheme, netloc, new_path, "", "", ""))

        return Response(
            json.dumps(
                {
                    "link_b64": base64.b64encode(final_url.encode("utf-8")).decode("ascii"),
                    "alg_used": alg,
                    "ecdsa_format_used": (ecdsa_format if alg == "ecdsa_p256" else None),
                }
            ),
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("sign_link error")
        return Response(
            json.dumps({"error": str(e)}),
            status=400,
            mimetype="application/json",
        )