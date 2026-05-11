import json

from flask import Blueprint, Response

bp = Blueprint("misc", __name__)


@bp.route("/health", methods=["GET"])
def health():
    body = {"status": "ok", "service": "KSeF RSA Encryptor"}
    return Response(
        json.dumps(body, separators=(",", ":")),
        mimetype="application/json",
    )


@bp.route("/", methods=["GET"])
def index():
    body = {
        "service": "KSeF RSA Encryptor 1.2.0",
        "docs": "/apidocs",
        "health": "/health",
        "generate_pdf": "/generatePDF",
    }
    return Response(
        json.dumps(body, separators=(",", ":")),
        mimetype="application/json",
    )