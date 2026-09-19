import json
import os
import subprocess

from core.pdf_errors import (
    GENERATOR_BAD_RESPONSE,
    GENERATOR_EMPTY_OUTPUT,
    GENERATOR_TIMEOUT,
    GENERATOR_UNAVAILABLE,
    PdfServiceError,
    classify_generator_failure,
)


SUPPORTED_LANGUAGES = {"pl", "en"}


ERROR_MARKER = "__KSEF_PDF_ERROR__"


def _extract_bridge_error(stderr: str | None) -> str:
    """
    Pull the bridge's own error out of stderr.

    stderr also carries i18next debug output from the PDF module, so without the
    marker the real cause ends up buried under unrelated log lines.
    """
    stderr_text = (stderr or "").strip()

    if ERROR_MARKER in stderr_text:
        return stderr_text.rsplit(ERROR_MARKER, 1)[1].strip() or "Unknown PDF generator error"

    return stderr_text or "Unknown PDF generator error"


def run_pdf_generator(xml_content: str, additional_data: dict, language: str = "pl") -> str:
    node_bin = os.getenv("KSEF_NODE_BIN", "node")
    bridge_path = os.getenv(
        "KSEF_PDF_BRIDGE_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "pdf_generator_bridge.mjs",
        ),
    )
    timeout_seconds = float(os.getenv("KSEF_PDF_TIMEOUT_SECONDS", "60"))

    payload = json.dumps(
        {
            "xmlContent": xml_content,
            "additionalData": additional_data,
            "language": language,
        },
        separators=(",", ":"),
    )

    try:
        process = subprocess.run(
            [node_bin, bridge_path],
            input=payload,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise PdfServiceError(
            GENERATOR_UNAVAILABLE,
            "Node.js executable not found. Set KSEF_NODE_BIN or install node.",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        # 504 rather than 500: the work may well succeed on a retry, and the caller
        # needs that apart from the faults that will fail again the same way.
        raise PdfServiceError(
            GENERATOR_TIMEOUT,
            f"PDF generator did not finish within {timeout_seconds:g} s.",
            status=504,
        ) from exc

    if process.returncode != 0:
        raise classify_generator_failure(_extract_bridge_error(process.stderr))

    try:
        output_data = json.loads(process.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise PdfServiceError(GENERATOR_BAD_RESPONSE, "Invalid PDF generator response.") from exc

    pdf_b64 = output_data.get("base64")
    if not isinstance(pdf_b64, str) or not pdf_b64:
        raise PdfServiceError(GENERATOR_EMPTY_OUTPUT, "PDF generator returned empty output.")

    return pdf_b64


def normalize_pdf_additional_data(additional_data) -> dict:
    normalized = {}

    if not isinstance(additional_data, dict):
        return normalized

    nr_ksef = additional_data.get("nr_ksef")
    if nr_ksef is None:
        nr_ksef = additional_data.get("nrKSeF")
    if nr_ksef is not None:
        normalized["nrKSeF"] = str(nr_ksef)

    ac_date = additional_data.get("ac_date")
    if ac_date is None:
        ac_date = additional_data.get("acDate")
    if ac_date is not None:
        normalized["acDate"] = str(ac_date)

    qr_code = additional_data.get("qr_code")
    if qr_code is None:
        qr_code = additional_data.get("qrCode")
    if qr_code is not None:
        normalized["qrCode"] = str(qr_code)

    qr2_code = additional_data.get("qr2_code")
    if qr2_code is None:
        qr2_code = additional_data.get("qr2Code")
    if qr2_code is not None:
        normalized["qr2Code"] = str(qr2_code)

    is_mobile = additional_data.get("is_mobile")
    if is_mobile is None:
        is_mobile = additional_data.get("isMobile")
    if is_mobile is not None:
        if isinstance(is_mobile, str):
            normalized["isMobile"] = is_mobile.strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
            }
        else:
            normalized["isMobile"] = bool(is_mobile)

    watermark = additional_data.get("watermark")
    if watermark is not None:
        normalized["watermark"] = str(watermark)

    return normalized
