"""Work-order DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CoordinatorPlanView:
    worker_employee_id: str
    selection_reason: str
    required_tools: list[str]
    matched_terms: list[str]


@dataclass(slots=True)
class CreateWorkOrderRequest:
    employee_id: str
    input_text: str
    budget_tokens: int
    tenant: str | None
    config_snapshot_id: str | None
    execution_mode: str = "single"
    coordinator_participants: list[str] | None = None


@dataclass(slots=True)
class WorkOrderView:
    work_order_id: str
    employee_id: str
    tenant: str | None
    config_snapshot_id: str | None
    execution_mode: str
    coordinator_participants: list[str]
    coordinator_plan: CoordinatorPlanView | None
    status: str
    budget_tokens: int
    input_text: str
    output_summary: str
    last_session_id: str | None
    last_approval_id: str | None
    last_error: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class RunWorkOrderView:
    work_order_id: str
    session_id: str
    task_id: str
    status: str
    output_summary: str
    budget_used: int
    budget_remaining: int
