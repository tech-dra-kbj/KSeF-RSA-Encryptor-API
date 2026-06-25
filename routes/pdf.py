import base64
import json
import logging

from flask import Blueprint, Response, request

from core.pdf_service import normalize_pdf_additional_data, run_pdf_generator

bp = Blueprint("pdf", __name__)


@bp.route("/generatePDF", methods=["POST"])
def generate_pdf():
    try:
        body = request.get_json(force=True, silent=False)

        if not isinstance(body, dict):
            return Response(
                json.dumps({"error": "Body musi być obiektem JSON."}),
                status=400,
                mimetype="application/json",
            )

        xml_b64 = body.get("xml_b64")
        response_type = (body.get("response_type") or "base64").lower()
        additional_data = body.get("additional_data") or {}

        if not isinstance(xml_b64, str) or not xml_b64.strip():
            return Response(
                json.dumps({"error": "Wymagane: 'xml_b64' (Base64 zakodowany XML)."}),
                status=400,
                mimetype="application/json",
            )

        if response_type not in {"base64", "binary"}:
            return Response(
                json.dumps({"error": "response_type musi być 'base64' albo 'binary'."}),
                status=400,
                mimetype="application/json",
            )

        if not isinstance(additional_data, dict):
            return Response(
                json.dumps({"error": "additional_data musi być obiektem JSON."}),
                status=400,
                mimetype="application/json",
            )

        try:
            xml_bytes = base64.b64decode(xml_b64, validate=True)
        except Exception as exc:
            return Response(
                json.dumps({"error": f"Błąd Base64 w xml_b64: {exc}"}),
                status=400,
                mimetype="application/json",
            )

        try:
            xml_content = xml_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            return Response(
                json.dumps({"error": f"xml_b64 nie zawiera poprawnego UTF-8 XML: {exc}"}),
                status=400,
                mimetype="application/json",
            )

        additional_data_mapped = normalize_pdf_additional_data(additional_data)
        pdf_b64 = run_pdf_generator(xml_content, additional_data_mapped)

        if response_type == "binary":
            try:
                pdf_bytes = base64.b64decode(pdf_b64, validate=True)
            except Exception as exc:
                raise RuntimeError(f"Invalid Base64 PDF payload: {exc}") from exc

            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={"Content-Disposition": 'inline; filename="invoice.pdf"'},
            )

        return Response(
            json.dumps({"status": "ok", "pdf_b64": pdf_b64}, separators=(",", ":")),
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("generate_pdf error")
        return Response(
            json.dumps({"error": str(e)}),
            status=500,
            mimetype="application/json",
        )