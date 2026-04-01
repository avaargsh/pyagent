"""DTOs shared by CLI and future APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from digital_employee.domain.errors import DigitalEmployeeError


class CommandFailure(Exception):
    """Structured command failure."""

    def __init__(self, code: int, error_type: str, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.error_type = error_type
        self.message = message
        self.hint = hint


class ConfigInvalid(Exception):
    """Raised when loaded configuration fails validation."""

    def __init__(self, issues: list[str], message: str) -> None:
        super().__init__(message)
        self.issues = issues
        self.message = message


def command_failure_from_error(error: DigitalEmployeeError) -> CommandFailure:
    return CommandFailure(
        code=error.exit_code,
        error_type=error.error_type,
        message=error.message,
        hint=error.hint,
    )


@dataclass(slots=True)
class CommandResult:
    command: str
    data: dict[str, Any]
    human_lines: list[str]
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StreamResult:
    command: str
    exit_code: int = 0
