"""Tool definition models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from digital_employee.domain.tool_call import ToolObservation


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[ToolObservation]]
    resource_kind: str = "generic"
    risk_level: str = "low"
    permission_mode: str = "auto"
    side_effects: str = "none"
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    requires_approval: bool = False
    timeout_seconds: int = 30
