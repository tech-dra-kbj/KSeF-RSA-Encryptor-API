import base64
import json
import logging

from flask import Blueprint, Response, request
from werkzeug.exceptions import BadRequest

from core.b64 import Base64Error, decode_b64
from core.pdf_errors import (
    ADDITIONAL_DATA_NOT_OBJECT,
    BODY_NOT_JSON,
    BODY_NOT_OBJECT,
    GENERATOR_BAD_RESPONSE,
    LANGUAGE_UNSUPPORTED,
    RESPONSE_TYPE_INVALID,
    UNEXPECTED,
    XML_B64_MISSING,
    XML_B64_NOT_BASE64,
    XML_B64_NOT_UTF8,
    PdfError,
    PdfRequestError,
    PdfServiceError,
)
from core.pdf_service import normalize_pdf_additional_data, run_pdf_generator

bp = Blueprint("pdf", __name__)


def _error(code: int, message: str, status: int) -> Response:
    """
    Error envelope shared with /encrypt (see routes/legacy_encrypt.py).

    `error` repeats `message` so callers written against the previous contract keep
    working; it is deprecated and will go once they have moved to `code`.
    """
    return Response(
        json.dumps(
            {"status": "error", "code": code, "message": message, "error": message},
            ensure_ascii=False,
        ),
        status=status,
        mimetype="application/json",
    )


def _fail(exc: PdfError) -> Response:
    return _error(exc.code, exc.message, exc.status)


@bp.route("/generatePDF", methods=["POST"])
def generate_pdf():
    try:
        try:
            body = request.get_json(force=True, silent=False)
        except BadRequest as exc:
            raise PdfRequestError(BODY_NOT_JSON, "Request body is not valid JSON.") from exc

        if not isinstance(body, dict):
            raise PdfRequestError(BODY_NOT_OBJECT, "Body must be a JSON object.")

        xml_b64 = body.get("xml_b64")
        response_type = (body.get("response_type") or "base64").lower()
        additional_data = body.get("additional_data") or {}

        if not isinstance(xml_b64, str) or not xml_b64.strip():
            raise PdfRequestError(
                XML_B64_MISSING, "Field 'xml_b64' is required and must be a Base64-encoded XML string."
            )

        if response_type not in {"base64", "binary"}:
            raise PdfRequestError(RESPONSE_TYPE_INVALID, "response_type must be 'base64' or 'binary'.")

        if not isinstance(additional_data, dict):
            raise PdfRequestError(ADDITIONAL_DATA_NOT_OBJECT, "additional_data must be a JSON object.")

        language = (additional_data.get("language") or "pl").lower()

        if language not in {"pl", "en"}:
            raise PdfRequestError(LANGUAGE_UNSUPPORTED, "additional_data.language must be 'pl' or 'en'.")

        try:
            xml_bytes = decode_b64(xml_b64, "xml_b64")
        except Base64Error as exc:
            raise PdfRequestError(XML_B64_NOT_BASE64, str(exc)) from exc

        try:
            xml_content = xml_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PdfRequestError(XML_B64_NOT_UTF8, f"xml_b64 does not decode to UTF-8 text: {exc}") from exc

        additional_data_mapped = normalize_pdf_additional_data(additional_data)
        pdf_b64 = run_pdf_generator(xml_content, additional_data_mapped, language)

        if response_type == "binary":
            try:
                pdf_bytes = base64.b64decode(pdf_b64, validate=True)
            except Exception as exc:
                raise PdfServiceError(
                    GENERATOR_BAD_RESPONSE, f"Generator returned an invalid Base64 payload: {exc}"
                ) from exc

            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={"Content-Disposition": 'inline; filename="invoice.pdf"'},
            )

        return Response(
            json.dumps({"status": "ok", "pdf_b64": pdf_b64}, separators=(",", ":")),
            mimetype="application/json",
        )

    except PdfError as exc:
        if exc.status >= 500:
            logging.exception("generate_pdf failed with code %s", exc.code)
        else:
            logging.info("generate_pdf rejected request with code %s: %s", exc.code, exc.message)
        return _fail(exc)

    except Exception as exc:
        logging.exception("generate_pdf unexpected error")
        return _error(UNEXPECTED, str(exc), 500)
