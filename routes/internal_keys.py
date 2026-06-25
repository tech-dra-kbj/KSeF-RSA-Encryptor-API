import json
import logging

from flask import Blueprint, Response, request

from core.key_manager import get_or_create_key

bp = Blueprint("internal_keys", __name__)


@bp.route("/get_pub_cert", methods=["POST"])
def get_pub_cert():
    try:
        body = request.get_json(force=True, silent=False)

        if not isinstance(body, dict):
            return Response(
                json.dumps({"error": "Body must be a JSON object."}),
                status=400,
                mimetype="application/json",
            )

        sid = body.get("sid")

        if not sid:
            return Response(
                json.dumps({"error": "Missing required field: 'sid'."}),
                status=400,
                mimetype="application/json",
            )

        try:
            result = get_or_create_key(sid)
        except ValueError as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status=400,
                mimetype="application/json",
            )

        return Response(
            json.dumps(result, separators=(",", ":")),
            mimetype="application/json",
        )

    except Exception as exc:
        logging.exception("get_pub_cert error")
        return Response(
            json.dumps({"error": str(exc)}),
            status=500,
            mimetype="application/json",
        )