import json
import os
import subprocess


def run_pdf_generator(xml_content: str, additional_data: dict) -> str:
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
        raise RuntimeError("Node.js executable not found. Set KSEF_NODE_BIN or install node.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("PDF generator timeout") from exc

    if process.returncode != 0:
        stderr_text = (process.stderr or "").strip()
        error_message = stderr_text or "Unknown PDF generator error"
        raise RuntimeError(f"PDF generator failed: {error_message}")

    try:
        output_data = json.loads(process.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid PDF generator response") from exc

    pdf_b64 = output_data.get("base64")
    if not isinstance(pdf_b64, str) or not pdf_b64:
        raise RuntimeError("PDF generator returned empty output")

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

    return normalized