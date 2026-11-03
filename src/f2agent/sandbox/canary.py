"""Canary strings: unique markers planted in mock secrets to detect exfiltration."""

import re
from typing import Any

CANARY_RE = re.compile(r"CANARY-[0-9a-f]{8}")
REDACTED = "CANARY-<redacted>"


def find_canaries(text: str) -> set[str]:
    """Return every canary string that appears in ``text``."""
    return set(CANARY_RE.findall(text))


def redact(value: Any) -> Any:
    """Recursively replace canaries in strings, lists and dicts."""
    if isinstance(value, str):
        return CANARY_RE.sub(REDACTED, value)
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value
