import base64
import json
import logging

from flask import Blueprint, Response, request

from core.consume_service import decrypt_request, encrypt_response

bp = Blueprint("consume", __name__)


@bp.route("/consume", methods=["POST"])
def consume():
    try:
        body = request.get_json(force=True, silent=False)

        if not isinstance(body, dict):
            return Response(
                json.dumps({"error": "Body must be a JSON object."}),
                status=400,
                mimetype="application/json",
            )

        required = ["sid", "kid", "enc_key_b64", "iv_b64", "ciphertext_b64"]
        missing = [k for k in required if not body.get(k)]

        if missing:
            return Response(
                json.dumps({"error": f"Missing required fields: {', '.join(missing)}"}),
                status=400,
                mimetype="application/json",
            )

        try:
            result = decrypt_request(body)
        except Exception as e:
            return Response(
                json.dumps({"error": f"Decrypt error: {str(e)}"}),
                status=400,
                mimetype="application/json",
            )

        plaintext = result["plaintext"]

        # For now: echo decrypted payload.
        # Later this will dispatch internal target, e.g. /encrypt.
        response_payload = plaintext

        reply_pub = body.get("reply_public_key_pem_b64")

        # If no reply key is provided, return plaintext for debug/testing.
        if not reply_pub:
            return Response(
                json.dumps(
                    {
                        "status": "ok",
                        "plaintext_b64": base64.b64encode(response_payload).decode("ascii"),
                    },
                    separators=(",", ":"),
                ),
                mimetype="application/json",
            )

        try:
            encrypted = encrypt_response(response_payload, reply_pub)
        except Exception as e:
            return Response(
                json.dumps({"error": f"Encrypt response error: {str(e)}"}),
                status=400,
                mimetype="application/json",
            )

        return Response(
            json.dumps(
                {
                    "status": "ok",
                    "reply": encrypted,
                },
                separators=(",", ":"),
            ),
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("consume error")
        return Response(
            json.dumps({"error": str(e)}),
            status=500,
            mimetype="application/json",
        )