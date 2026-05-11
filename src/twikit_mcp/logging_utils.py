"""Logging helpers with conservative secret redaction."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


REDACTED = "***REDACTED***"
SECRET_KEYS = {
    "auth_token",
    "ct0",
    "authorization",
    "cookie",
    "cookies",
}


def redact_secrets(value: Any) -> Any:
    """Return a copy of value with known secret fields redacted."""
    if isinstance(value, Mapping):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SECRET_KEYS:
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    return value
