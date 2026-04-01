"""Shared CLI helpers."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from typing import Any

from digital_employee.application.dto.common import CommandFailure, CommandResult


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def emit_result(result: CommandResult, as_json: bool, request_id: str | None, trace_id: str | None) -> None:
    payload = {
        "schema_version": 1,
        "command": result.command,
        "ok": True,
        "data": _normalize(result.data),
        "error": None,
        "meta": {
            "request_id": request_id,
            "trace_id": trace_id,
        },
    }
    if as_json:
        json.dump(payload, sys.stdout, ensure_ascii=True, indent=2)
        sys.stdout.write("\n")
        return

    for line in result.human_lines:
        sys.stdout.write(f"{line}\n")


def emit_error(
    command: str,
    error: CommandFailure,
    as_json: bool,
    request_id: str | None,
    trace_id: str | None,
) -> None:
    payload = {
        "schema_version": 1,
        "command": command,
        "ok": False,
        "data": None,
        "error": {
            "code": error.code,
            "type": error.error_type,
            "message": error.message,
            "hint": error.hint,
        },
        "meta": {
            "request_id": request_id,
            "trace_id": trace_id,
        },
    }
    if as_json:
        json.dump(payload, sys.stdout, ensure_ascii=True, indent=2)
        sys.stdout.write("\n")
        return

    sys.stderr.write(f"{error.message}\n")
    if error.hint:
        sys.stderr.write(f"Hint: {error.hint}\n")


def resolve_text_input(args, required: bool, prompt_label: str) -> str | None:
    if getattr(args, "input_file", None):
        from pathlib import Path

        try:
            return Path(args.input_file).read_text(encoding="utf-8").strip()
        except OSError as error:
            raise CommandFailure(
                2,
                "input_file_unreadable",
                f"failed to read input file: {args.input_file}",
                str(error),
            ) from error
    if getattr(args, "input_text", None):
        return args.input_text.strip()
    if not required:
        return None
    if args.no_input:
        raise CommandFailure(2, "input_required", "required input is missing", "pass --input or --input-file")
    if sys.stdin.isatty():
        value = input(f"{prompt_label}: ").strip()
        if value:
            return value
    raise CommandFailure(2, "input_required", "required input is missing", "pass --input or --input-file")


def resolve_json_input(args, required: bool, prompt_label: str) -> dict[str, Any] | None:
    raw_value = resolve_text_input(args, required=required, prompt_label=prompt_label)
    if raw_value is None:
        return None
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise CommandFailure(
            2,
            "json_input_invalid",
            "input must be valid JSON",
            str(error),
        ) from error
    if not isinstance(payload, dict):
        raise CommandFailure(
            2,
            "json_input_invalid",
            "input must be a JSON object",
            "pass a JSON object like '{\"query\":\"value\"}'",
        )
    return payload
