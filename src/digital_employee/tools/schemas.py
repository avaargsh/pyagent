"""Minimal schema validation helpers for tool payloads."""

from __future__ import annotations

from typing import Any

from digital_employee.domain.errors import ToolPayloadError


def validate_tool_payload(schema: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if schema.get("type") == "object" and not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    required = schema.get("required", [])
    for key in required:
        if key not in payload:
            issues.append(f"missing required field: {key}")

    properties = schema.get("properties", {})
    for key, value in payload.items():
        definition = properties.get(key)
        if definition is None:
            continue
        expected_type = definition.get("type")
        if expected_type == "string" and not isinstance(value, str):
            issues.append(f"field {key} must be a string")
        elif expected_type == "integer" and not isinstance(value, int):
            issues.append(f"field {key} must be an integer")
        elif expected_type == "number" and not isinstance(value, (int, float)):
            issues.append(f"field {key} must be a number")
        elif expected_type == "boolean" and not isinstance(value, bool):
            issues.append(f"field {key} must be a boolean")
        elif expected_type == "object" and not isinstance(value, dict):
            issues.append(f"field {key} must be an object")
    return issues


def ensure_valid_tool_payload(tool_name: str, schema: dict[str, Any], payload: dict[str, Any]) -> None:
    issues = validate_tool_payload(schema, payload)
    if issues:
        raise ToolPayloadError(tool_name, issues)
