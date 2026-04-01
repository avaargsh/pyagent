"""Session DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CoordinationView:
    execution_mode: str
    dispatch_mode: str | None
    coordinator_employee_id: str | None
    worker_employee_id: str | None
    participant_ids: list[str] = field(default_factory=list)
    selection_reason: str | None = None
    required_tools: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SessionView:
    session_id: str
    work_order_id: str | None
    employee_id: str | None
    status: str
    started_at: str
    ended_at: str | None
    turns: int
    budget_used: int
    budget_remaining: int
    current_stage: str
    coordination: CoordinationView | None = None


@dataclass(slots=True)
class SessionExportView:
    session: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)
    coordination: CoordinationView | None = None
