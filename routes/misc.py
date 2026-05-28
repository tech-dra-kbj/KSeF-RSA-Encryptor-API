import json

from flask import Blueprint, Response

bp = Blueprint("misc", __name__)


@bp.route("/health", methods=["GET"])
def health():
    body = {"status": "ok", "service": "KSeF Integration API", "version": "1.3.0"}
    return Response(
        json.dumps(body, separators=(",", ":")),
        mimetype="application/json",
    )


@bp.route("/", methods=["GET"])
def index():
    body = {
        "service": "KSeF Integration API 1.3.0",
        "docs": "/apidocs",
        "health": "/health",
        "generate_pdf": "/generatePDF",
    }
    return Response(
        json.dumps(body, separators=(",", ":")),
        mimetype="application/json",
    )