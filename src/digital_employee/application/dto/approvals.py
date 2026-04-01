"""Approval DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApprovalView:
    approval_id: str
    work_order_id: str | None
    session_id: str
    employee_id: str
    tool_name: str
    tool_payload: dict[str, Any]
    approval_policy: str
    requested_reason: str
    status: str
    created_at: str
    decided_at: str | None
    decision: str | None
    decision_reason: str | None
