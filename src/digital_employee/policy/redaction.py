"""Minimal payload redaction helpers."""

from __future__ import annotations


_SECRET_KEYS = {"api_key", "token", "password", "secret"}


def redact_payload(payload: dict) -> dict:
    redacted: dict = {}
    for key, value in payload.items():
        if key.lower() in _SECRET_KEYS:
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted
