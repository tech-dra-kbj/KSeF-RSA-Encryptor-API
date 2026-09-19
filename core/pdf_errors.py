"""
Error taxonomy for /generatePDF.

Codes follow the convention already used by /encrypt in routes/legacy_encrypt.py:
a numeric block per endpoint, with the block's `x99` reserved for "unexpected".
The 1xx block belongs to /encrypt; /generatePDF owns 2xxx:

    21xx  request is malformed            -> HTTP 400, caller must fix and not retry
    22xx  XML payload is unusable         -> HTTP 400, caller must fix and not retry
    23xx  service could not do its job    -> HTTP 5xx, retrying may succeed

The split matters more than the numbers: a consumer decides whether to retry from
the status class alone, and reads `code` only to report *why* without parsing prose.
"""

# 21xx — request validation
BODY_NOT_OBJECT = 2100
BODY_NOT_JSON = 2101
XML_B64_MISSING = 2102
XML_B64_NOT_BASE64 = 2103
XML_B64_NOT_UTF8 = 2104
RESPONSE_TYPE_INVALID = 2105
ADDITIONAL_DATA_NOT_OBJECT = 2106
LANGUAGE_UNSUPPORTED = 2107

# 22xx — XML payload
XML_EMPTY = 2200
XML_MALFORMED = 2201
XML_SCHEMA_UNSUPPORTED = 2202

# 23xx — service faults
GENERATOR_TIMEOUT = 2300
GENERATOR_UNAVAILABLE = 2301
GENERATOR_BAD_RESPONSE = 2302
GENERATOR_EMPTY_OUTPUT = 2303
UNEXPECTED = 2399


class PdfError(Exception):
    """Carries the code and HTTP status that the route should return."""

    def __init__(self, code: int, message: str, status: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class PdfRequestError(PdfError):
    """Caller's fault — deterministic, retrying the same request cannot help."""

    def __init__(self, code: int, message: str):
        super().__init__(code, message, 400)


class PdfServiceError(PdfError):
    """Our fault — the same request may succeed later."""

    def __init__(self, code: int, message: str, status: int = 500):
        super().__init__(code, message, status)


# Substrings emitted by the upstream generator (sax parser and its own guards) that
# identify a bad payload rather than a broken service. Anything not listed here is
# treated as a service fault on purpose: mislabelling our own bug as the caller's
# would make the caller drop an invoice that a retry would have delivered.
_XML_MALFORMED_MARKERS = (
    "Text data outside of root node",
    "Unexpected close tag",
    "Unclosed root tag",
    "Unencoded <",
    "Invalid character",
    "Non-whitespace before first tag",
    "Unexpected end",
    "Attribute without value",
    "No whitespace between attributes",
    "Invalid tagname",
    "Unquoted attribute value",
    "Forward-slash in opening tag",
    "Unmatched closing tag",
    "Malformed XML",
)

_SCHEMA_MARKERS = (
    "Unknown XML Version",
    "Unsupported XML Version",
)


def classify_generator_failure(detail: str) -> PdfError:
    """Map a message from the Node bridge onto a code and an HTTP status."""
    text = (detail or "").strip()

    if "xmlContent is required" in text:
        return PdfRequestError(XML_EMPTY, "Decoded xml_b64 contains no XML content.")

    if any(m in text for m in _SCHEMA_MARKERS):
        return PdfRequestError(
            XML_SCHEMA_UNSUPPORTED,
            f"XML is not a recognised KSeF invoice document: {text}",
        )

    if any(m in text for m in _XML_MALFORMED_MARKERS):
        return PdfRequestError(XML_MALFORMED, f"XML is not well-formed: {text}")

    return PdfServiceError(UNEXPECTED, f"PDF generator failed: {text}")
