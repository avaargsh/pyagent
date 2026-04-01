"""Domain error hierarchy shared by runtime and CLI boundaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(eq=False)
class DigitalEmployeeError(Exception):
    message: str
    error_type: str
    exit_code: int = 1
    hint: str | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)


class ConfigError(DigitalEmployeeError):
    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(
            message=message,
            error_type="config_invalid",
            exit_code=3,
            hint=hint,
        )


def _normalize_resource_name(resource: str) -> str:
    return resource.replace(" ", "_").replace("-", "_")


class NotFoundError(DigitalEmployeeError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource} {identifier} was not found",
            error_type=f"{_normalize_resource_name(resource)}_not_found",
            exit_code=7,
        )


class ProviderNotFoundError(DigitalEmployeeError):
    def __init__(self, provider_name: str) -> None:
        super().__init__(
            message=f"provider {provider_name} was not found",
            error_type="provider_not_found",
            exit_code=6,
            hint="check the employee profile and configured providers",
        )


class ProviderExecutionError(DigitalEmployeeError):
    def __init__(self, provider_name: str, message: str, hint: str | None = None) -> None:
        super().__init__(
            message=f"provider {provider_name} failed: {message}",
            error_type="provider_error",
            exit_code=8,
            hint=hint,
        )


class ToolNotFoundError(DigitalEmployeeError):
    def __init__(self, tool_name: str) -> None:
        super().__init__(
            message=f"tool {tool_name} was not found",
            error_type="tool_not_found",
            exit_code=6,
            hint="check the configured tool registry for this employee",
        )


class ToolNotAllowedError(DigitalEmployeeError):
    def __init__(self, employee_id: str, tool_name: str) -> None:
        super().__init__(
            message=f"tool {tool_name} is denied for employee {employee_id}",
            error_type="tool_not_allowed",
            exit_code=4,
            hint="update the employee allow-list or choose a different tool",
        )


class ToolExecutionError(DigitalEmployeeError):
    def __init__(self, tool_name: str, message: str) -> None:
        super().__init__(
            message=f"tool {tool_name} failed: {message}",
            error_type="tool_error",
            exit_code=8,
        )


class ToolPayloadError(DigitalEmployeeError):
    def __init__(self, tool_name: str, issues: list[str]) -> None:
        summary = "; ".join(issues)
        super().__init__(
            message=f"tool {tool_name} payload is invalid: {summary}",
            error_type="tool_payload_invalid",
            exit_code=2,
            hint="fix the JSON payload to match the tool input schema",
        )


class BudgetExceededError(DigitalEmployeeError):
    def __init__(self, total_tokens: int, attempted_tokens: int) -> None:
        super().__init__(
            message=(
                f"budget exceeded: attempted to use {attempted_tokens} tokens "
                f"with a limit of {total_tokens}"
            ),
            error_type="budget_exceeded",
            exit_code=8,
            hint="increase the work-order budget or reduce tool/completion usage",
        )


class HookBlockedError(DigitalEmployeeError):
    def __init__(self, hook_point: str) -> None:
        super().__init__(
            message=f"execution was blocked by hook {hook_point}",
            error_type="hook_blocked",
            exit_code=4,
        )


class ApprovalRequiredError(DigitalEmployeeError):
    def __init__(self, approval_id: str, hint: str | None = None) -> None:
        super().__init__(
            message=f"approval {approval_id} requires a decision before the work order can continue",
            error_type="approval_required",
            exit_code=6,
            hint=hint,
        )
