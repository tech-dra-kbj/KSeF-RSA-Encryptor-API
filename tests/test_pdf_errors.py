import base64
import os
import subprocess
import tempfile

import pytest

import core.config as config
import core.database as database
import core.pdf_errors as codes
import core.pdf_service as pdf_service
import encrypt_service
from core.pdf_errors import PdfRequestError, PdfServiceError, classify_generator_failure


@pytest.fixture
def client(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        monkeypatch.setattr(config, "DB_PATH", db_path)
        monkeypatch.setattr(database, "DB_PATH", db_path)

        app = encrypt_service.create_app()
        app.config.update(TESTING=True)

        with app.test_client() as test_client:
            yield test_client


def b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def post(client, payload, raw=None):
    if raw is not None:
        return client.post("/generatePDF", data=raw, content_type="application/json")
    return client.post("/generatePDF", json=payload)


# --- 21xx: the request itself is malformed -------------------------------------

@pytest.mark.parametrize(
    "payload,expected",
    [
        ([1, 2], codes.BODY_NOT_OBJECT),
        ({}, codes.XML_B64_MISSING),
        ({"xml_b64": "   "}, codes.XML_B64_MISSING),
        ({"xml_b64": 123}, codes.XML_B64_MISSING),
        ({"xml_b64": "!!!"}, codes.XML_B64_NOT_BASE64),
        ({"xml_b64": "/v8AQQBC"}, codes.XML_B64_NOT_UTF8),
        ({"xml_b64": b64("<a/>"), "response_type": "pdf"}, codes.RESPONSE_TYPE_INVALID),
        ({"xml_b64": b64("<a/>"), "additional_data": "x"}, codes.ADDITIONAL_DATA_NOT_OBJECT),
        (
            {"xml_b64": b64("<a/>"), "additional_data": {"language": "de"}},
            codes.LANGUAGE_UNSUPPORTED,
        ),
    ],
)
def test_request_errors_are_400_with_code(client, payload, expected):
    response = post(client, payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"
    assert data["code"] == expected
    # `error` is kept as a deprecated alias of `message` for older callers.
    assert data["error"] == data["message"]


def test_malformed_json_body_is_400_not_500(client):
    response = post(client, None, raw="{not json")

    assert response.status_code == 400
    assert response.get_json()["code"] == codes.BODY_NOT_JSON


# --- 22xx: the XML payload is unusable -----------------------------------------

def test_empty_xml_is_client_error():
    error = classify_generator_failure("xmlContent is required")

    assert isinstance(error, PdfRequestError)
    assert error.code == codes.XML_EMPTY
    assert error.status == 400


@pytest.mark.parametrize(
    "detail",
    [
        "Text data outside of root node.\nLine: 0\nColumn: 15",
        "Unexpected close tag\nLine: 0\nColumn: 10",
        "Non-whitespace before first tag.",
    ],
)
def test_malformed_xml_is_client_error(detail):
    error = classify_generator_failure(detail)

    assert error.code == codes.XML_MALFORMED
    assert error.status == 400


def test_unrecognised_schema_is_client_error():
    error = classify_generator_failure("Unknown XML Version: undefined")

    assert error.code == codes.XML_SCHEMA_UNSUPPORTED
    assert error.status == 400


# --- 23xx: our fault ------------------------------------------------------------

def test_unrecognised_generator_failure_stays_a_server_error():
    """
    A message we do not recognise must not be blamed on the caller: doing so would
    tell them to stop retrying a fault that a retry could well clear.
    """
    error = classify_generator_failure("TypeError: cannot read property 'x' of undefined")

    assert isinstance(error, PdfServiceError)
    assert error.code == codes.UNEXPECTED
    assert error.status == 500


def test_timeout_maps_to_504(monkeypatch):
    def explode(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="node", timeout=60)

    monkeypatch.setattr(pdf_service.subprocess, "run", explode)

    with pytest.raises(PdfServiceError) as excinfo:
        pdf_service.run_pdf_generator("<a/>", {}, "pl")

    assert excinfo.value.code == codes.GENERATOR_TIMEOUT
    assert excinfo.value.status == 504


def test_missing_node_maps_to_unavailable(monkeypatch):
    def explode(*args, **kwargs):
        raise FileNotFoundError("node")

    monkeypatch.setattr(pdf_service.subprocess, "run", explode)

    with pytest.raises(PdfServiceError) as excinfo:
        pdf_service.run_pdf_generator("<a/>", {}, "pl")

    assert excinfo.value.code == codes.GENERATOR_UNAVAILABLE
    assert excinfo.value.status == 500


def test_codes_are_unique():
    """Two paths sharing a code would make the field useless for the caller."""
    values = [
        getattr(codes, name)
        for name in dir(codes)
        if name.isupper() and isinstance(getattr(codes, name), int)
    ]

    assert len(values) == len(set(values))


# --- documentation ---------------------------------------------------------------

def _source_codes():
    """Every numeric error code the service can actually return."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent
    found = set()

    for path in (root / "routes").glob("*.py"):
        found |= {int(c) for c in re.findall(r'"code":\s*(\d+)', path.read_text())}

    for _, value in re.findall(
        r"^([A-Z_]+)\s*=\s*(\d{3,4})$", (root / "core" / "pdf_errors.py").read_text(), re.M
    ):
        found.add(int(value))

    return found


def test_every_error_code_is_documented():
    """
    A code that exists but is not written down is worse than no code at all: the
    caller sees a number nobody can explain. Adding one means documenting it.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    docs = (root / "docs" / "api.md").read_text() + (root / "swaggerapi.yaml").read_text()

    undocumented = sorted(code for code in _source_codes() if f"`{code}`" not in docs)

    assert not undocumented, (
        f"Error codes missing from docs/api.md and swaggerapi.yaml: {undocumented}"
    )
