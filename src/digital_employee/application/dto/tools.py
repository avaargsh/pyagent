"""Tool DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolView:
    name: str
    description: str
    risk_level: str
    permission_mode: str
    applicable_employees: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolDetailView:
    name: str
    description: str
    input_schema: dict[str, Any]
    resource_kind: str
    risk_level: str
    permission_mode: str
    side_effects: str
    timeout_seconds: int
    requires_approval: bool
    is_read_only: bool
    is_concurrency_safe: bool
    applicable_employees: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolDryRunView:
    tool_name: str
    employee_id: str
    payload: dict[str, Any]
    policy_decision: str
    executable: bool
    approval_policy: str
    requires_approval: bool
