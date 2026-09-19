"""
One Base64 decoder for every endpoint.

Two behaviours differed across the service before this module existed, and both were
wrong in opposite directions:

* `base64.b64decode(value)` — the default — **silently discards** characters outside
  the Base64 alphabet. A corrupted payload decodes to a shorter one, or to nothing at
  all, and the request succeeds. `/encrypt` would happily encrypt zero bytes and return
  200, so the caller believed their token had been protected when nothing had been.
* `base64.b64decode(value, validate=True)` rejects whitespace, and therefore rejects
  line-wrapped Base64. Producers wrap routinely — ABAP, OpenSSL and anything that has
  passed through PEM emit 64- or 76-character lines — so strict validation alone turns
  ordinary input into an error.

Stripping whitespace first and validating the rest accepts what callers really send
while still refusing genuine garbage.
"""

import base64
import re

_WHITESPACE = re.compile(r"\s+")


class Base64Error(ValueError):
    """Raised when the input is not Base64 once whitespace has been removed."""


def decode_b64(value, field: str = "value") -> bytes:
    """Decode Base64, tolerating line wrapping and rejecting everything else."""
    if not isinstance(value, str):
        raise Base64Error(f"{field} must be a Base64-encoded string.")

    compact = _WHITESPACE.sub("", value)

    try:
        return base64.b64decode(compact, validate=True)
    except Exception as exc:
        raise Base64Error(f"{field} is not valid Base64: {exc}") from exc
