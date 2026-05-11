import base64
import json
import logging

from flask import Blueprint, Response, request
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key
from lxml import etree
from signxml import methods
from signxml.xades import XAdESSigner

bp = Blueprint("sign_xml", __name__)


@bp.route("/sign_xml", methods=["POST"])
def sign_xml():
    try:
        body = request.get_json(force=True, silent=False)

        xml_b64 = body.get("xml_b64")
        cert_pem_b64 = body.get("cert_pem_b64")
        key_pem_b64 = body.get("key_pem_b64")
        key_password_b64 = body.get("key_password_b64")
        alg = (body.get("alg") or "rsa_sha256").lower()

        if not xml_b64 or not cert_pem_b64 or not key_pem_b64:
            return Response(
                json.dumps({"error": "Wymagane: 'xml_b64', 'cert_pem_b64', 'key_pem_b64'."}),
                status=400,
                mimetype="application/json",
            )

        try:
            xml_bytes = base64.b64decode(xml_b64)
        except Exception as e:
            return Response(
                json.dumps({"error": f"Błąd Base64 w xml_b64: {e}"}),
                status=400,
                mimetype="application/json",
            )

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

        root = etree.fromstring(xml_bytes)

        signer = XAdESSigner(
            method=methods.enveloped,
            signature_algorithm=signature_algorithm,
            c14n_algorithm="http://www.w3.org/2006/12/xml-c14n11",
        )

        try:
            signer.add_signing_time()
        except Exception:
            pass

        try:
            signer.add_signing_certificate(cert_pem_str)
        except Exception:
            pass

        signed_root = signer.sign(data=root, key=key, cert=cert_pem_str)
        signed_xml_bytes = etree.tostring(
            signed_root,
            xml_declaration=True,
            encoding="utf-8",
        )

        return Response(
            json.dumps(
                {
                    "signed_xml_b64": base64.b64encode(signed_xml_bytes).decode("ascii"),
                    "alg_used": alg,
                }
            ),
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("XAdES signing error")
        return Response(
            json.dumps({"error": str(e)}),
            status=400,
            mimetype="application/json",
        )