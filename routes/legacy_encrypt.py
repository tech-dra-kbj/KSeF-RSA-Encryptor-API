import base64
import json

from flask import Blueprint, Response, request

from core.ksef_encrypt import encrypt_rsa_oaep, load_ksef_public_key_from_string

bp = Blueprint("legacy_encrypt", __name__)


@bp.route("/encrypt", methods=["POST"])
def encrypt_endpoint():
    try:
        payload = request.get_json(force=True)

        data_b64 = payload.get("data_b64")
        cert_b64 = payload.get("cert_b64")

        if not data_b64 or not cert_b64:
            body = {"status": "error", "code": 101, "message": "Brak wymaganych pól"}
            return Response(
                json.dumps(body, separators=(",", ":")),
                status=400,
                mimetype="application/json",
            )

        try:
            data = base64.b64decode(data_b64)
        except Exception as e:
            body = {"status": "error", "code": 102, "message": f"Błąd Base64: {e}"}
            return Response(
                json.dumps(body, separators=(",", ":")),
                status=400,
                mimetype="application/json",
            )

        try:
            public_key = load_ksef_public_key_from_string(cert_b64)
        except Exception as e:
            body = {"status": "error", "code": 103, "message": str(e)}
            return Response(
                json.dumps(body, separators=(",", ":")),
                status=400,
                mimetype="application/json",
            )

        try:
            encrypted = encrypt_rsa_oaep(public_key, data)
        except Exception as e:
            body = {"status": "error", "code": 104, "message": f"Błąd szyfrowania: {e}"}
            return Response(
                json.dumps(body, separators=(",", ":")),
                status=500,
                mimetype="application/json",
            )

        encrypted_b64 = base64.b64encode(encrypted).decode("ascii")
        body = {"status": "ok", "encrypted_b64": encrypted_b64}

        return Response(
            json.dumps(body, separators=(",", ":")),
            mimetype="application/json",
        )

    except Exception as e:
        body = {"status": "error", "code": 199, "message": f"Nieoczekiwany błąd: {e}"}
        return Response(
            json.dumps(body, separators=(",", ":")),
            status=500,
            mimetype="application/json",
        )