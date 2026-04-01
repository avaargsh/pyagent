"""Entrypoint for the dectl CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from digital_employee.api.cli import (
    approval_cmd,
    config_cmd,
    doctor_cmd,
    employee_cmd,
    replay_cmd,
    session_cmd,
    tool_cmd,
    version_cmd,
    work_order_cmd,
)
from digital_employee.api.cli.common import emit_error, emit_result
from digital_employee.application.dto.common import CommandFailure, StreamResult, command_failure_from_error
from digital_employee.application.services.request_context import build_app_context
from digital_employee.domain.errors import ConfigError, DigitalEmployeeError

_COMMANDS_ALLOWING_INVALID_CONFIG = frozenset({"config show", "config validate", "version"})
_COMMANDS_ALLOWING_JSONL = frozenset({"session tail", "work-order watch"})

# Compatibility alias retained so existing tests and call sites can still patch the
# control-plane builder at this module boundary.
build_deps = build_app_context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dectl")
    parser.add_argument("--profile")
    parser.add_argument("--tenant")
    parser.add_argument("--json", action="store_true", help="Emit a single JSON object to stdout.")
    parser.add_argument("--jsonl", action="store_true", help="Emit a JSON line stream when supported.")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--base-url")
    parser.add_argument("--no-input", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--trace-id")
    parser.add_argument("--request-id")

    subparsers = parser.add_subparsers(dest="resource")
    config_cmd.register(subparsers)
    employee_cmd.register(subparsers)
    work_order_cmd.register(subparsers)
    approval_cmd.register(subparsers)
    session_cmd.register(subparsers)
    tool_cmd.register(subparsers)
    replay_cmd.register(subparsers)
    doctor_cmd.register(subparsers)
    version_cmd.register(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2

    command_name = getattr(args, "command_name", args.resource or "unknown")
    as_json = getattr(args, "json", False)
    request_id = getattr(args, "request_id", None)
    trace_id = getattr(args, "trace_id", None)

    try:
        context = build_deps(
            root_path=Path.cwd(),
            profile=args.profile,
            tenant=args.tenant,
            base_url_override=args.base_url,
            timeout_override=args.timeout,
            output_json=args.json,
            no_input=args.no_input,
        )

        if getattr(args, "jsonl", False) and command_name not in _COMMANDS_ALLOWING_JSONL:
            raise CommandFailure(
                2,
                "jsonl_not_supported",
                f"{command_name} does not support --jsonl",
                "use --json for non-streaming commands",
            )

        if context.validation_issues and command_name not in _COMMANDS_ALLOWING_INVALID_CONFIG:
            summary = "; ".join(context.validation_issues)
            raise ConfigError(
                message=f"configuration is invalid: {summary}",
                hint="run 'dectl config validate' for details",
            )

        result = handler(args, context)
        if isinstance(result, StreamResult):
            return result.exit_code
        emit_result(result, as_json, request_id, trace_id)
        return 0
    except ConfigError as error:
        failure = command_failure_from_error(error)
        emit_error(command_name, failure, as_json, request_id, trace_id)
        return failure.code
    except CommandFailure as error:
        emit_error(command_name, error, as_json, request_id, trace_id)
        return error.code
    except DigitalEmployeeError as error:
        failure = command_failure_from_error(error)
        emit_error(command_name, failure, as_json, request_id, trace_id)
        return failure.code
    except KeyboardInterrupt:
        return 130
    except Exception:
        failure = CommandFailure(
            code=10,
            error_type="internal_error",
            message="an unexpected error occurred",
            hint=None if as_json else "check logs or rerun in a debug environment",
        )
        emit_error(command_name, failure, as_json, request_id, trace_id)
        return failure.code


if __name__ == "__main__":
    raise SystemExit(main())
