import base64

import pytest

from core.b64 import Base64Error, decode_b64


def test_plain_base64_decodes():
    assert decode_b64(base64.b64encode(b"<a/>").decode()) == b"<a/>"


@pytest.mark.parametrize("wrapped", ["PGEv\nPg==", "PGEv\r\nPg==", " PGEvPg== ", "PGEv Pg=="])
def test_line_wrapping_is_tolerated(wrapped):
    """
    ABAP, OpenSSL and anything that has been through PEM wrap Base64 at 64 or 76
    characters. Rejecting that would break ordinary callers.
    """
    assert decode_b64(wrapped) == b"<a/>"


@pytest.mark.parametrize("garbage", ["!!!", "nie base64 @@@", "PGEvPg==%%%"])
def test_garbage_is_rejected_not_silently_truncated(garbage):
    """
    The bare b64decode default drops characters outside the alphabet, so corrupt input
    decodes to something shorter — or to nothing — and the request succeeds. /encrypt
    used to return 200 having encrypted zero bytes.
    """
    with pytest.raises(Base64Error):
        decode_b64(garbage)


def test_non_string_is_rejected():
    with pytest.raises(Base64Error):
        decode_b64(123)


def test_field_name_reaches_the_message():
    with pytest.raises(Base64Error, match="xml_b64"):
        decode_b64("!!!", "xml_b64")


def test_no_endpoint_decodes_base64_loosely():
    """
    Every route must go through decode_b64. A bare base64.b64decode without
    validate=True reintroduces the silent-truncation bug this module exists to stop.
    """
    import pathlib
    import re

    offenders = []
    for path in (pathlib.Path(__file__).resolve().parent.parent / "routes").glob("*.py"):
        for line_no, line in enumerate(path.read_text().splitlines(), 1):
            if "base64.b64decode(" in line and "validate=True" not in line:
                offenders.append(f"{path.name}:{line_no}")

    assert not offenders, f"Loose base64.b64decode calls: {offenders}"
