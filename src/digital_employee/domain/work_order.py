"""Work-order model."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
from secrets import token_hex

from digital_employee.domain.artifact import ArtifactRef
from digital_employee.domain.enums import WorkOrderStatus
from digital_employee.domain.runtime_constraints import (
    ExecutionMode,
    normalize_execution_mode,
    normalize_participant_ids,
    normalize_string_list,
)
from digital_employee.domain.task_step import TaskStep


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _generate_work_order_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"wo_{stamp}_{token_hex(3)}"


@dataclass(slots=True)
class CoordinatorPlan:
    worker_employee_id: str
    selection_reason: str
    required_tools: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.worker_employee_id = str(self.worker_employee_id).strip()
        if not self.worker_employee_id:
            raise ValueError("coordinator_plan.worker_employee_id is required")
        self.selection_reason = str(self.selection_reason).strip() or "unknown"
        self.required_tools = normalize_string_list(self.required_tools)
        self.matched_terms = normalize_string_list(self.matched_terms)


@dataclass(slots=True)
class WorkOrder:
    work_order_id: str
    employee_id: str
    input_text: str
    tenant: str | None
    config_snapshot_id: str | None
    budget_tokens: int
    execution_mode: ExecutionMode = ExecutionMode.SINGLE
    coordinator_participants: list[str] = field(default_factory=list)
    coordinator_plan: CoordinatorPlan | None = None
    status: str = WorkOrderStatus.PENDING.value
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    steps: list[TaskStep] = field(default_factory=list)
    artifacts: list[ArtifactRef] = field(default_factory=list)
    last_session_id: str | None = None
    last_approval_id: str | None = None
    output_summary: str = ""
    last_error: str | None = None

    def __post_init__(self) -> None:
        self.execution_mode = normalize_execution_mode(self.execution_mode)
        self.coordinator_participants = normalize_participant_ids(self.coordinator_participants)
        if self.execution_mode == ExecutionMode.SINGLE:
            if self.coordinator_participants or self.coordinator_plan is not None:
                raise ValueError("single work order cannot define coordinator participants or plan")
            return
        if not self.coordinator_participants:
            raise ValueError("coordinated work order requires at least one participant")
        if (
            self.coordinator_plan is not None
            and self.coordinator_plan.worker_employee_id not in self.coordinator_participants
        ):
            raise ValueError("coordinator_plan.worker_employee_id must be listed in coordinator_participants")

    @classmethod
    def create_new(
        cls,
        employee_id: str,
        input_text: str,
        budget_tokens: int,
        tenant: str | None,
        config_snapshot_id: str | None = None,
        execution_mode: str = ExecutionMode.SINGLE.value,
        coordinator_participants: list[str] | None = None,
        coordinator_plan: CoordinatorPlan | None = None,
    ) -> "WorkOrder":
        return cls(
            work_order_id=_generate_work_order_id(),
            employee_id=employee_id,
            input_text=input_text,
            tenant=tenant,
            config_snapshot_id=config_snapshot_id,
            budget_tokens=budget_tokens,
            execution_mode=execution_mode,
            coordinator_participants=list(coordinator_participants or []),
            coordinator_plan=coordinator_plan,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def mark_running(self) -> None:
        self.status = WorkOrderStatus.RUNNING.value
        self.last_error = None
        self.updated_at = _now()

    def mark_completed(self, output_summary: str, session_id: str | None = None) -> None:
        self.status = WorkOrderStatus.COMPLETED.value
        self.output_summary = output_summary
        self.last_session_id = session_id
        self.last_approval_id = None
        self.last_error = None
        self.updated_at = _now()

    def mark_failed(self, error_message: str, session_id: str | None = None) -> None:
        self.status = WorkOrderStatus.FAILED.value
        self.last_error = error_message
        self.last_session_id = session_id
        self.updated_at = _now()

    def mark_waiting_approval(self, approval_id: str, session_id: str | None = None) -> None:
        self.status = WorkOrderStatus.WAITING_APPROVAL.value
        self.last_approval_id = approval_id
        self.last_session_id = session_id
        self.last_error = None
        self.updated_at = _now()

    def mark_cancelled(self, session_id: str | None = None, reason: str | None = None) -> None:
        self.status = WorkOrderStatus.CANCELLED.value
        self.last_session_id = session_id
        self.last_error = reason
        self.updated_at = _now()

    def add_artifact(self, artifact: ArtifactRef) -> None:
        self.artifacts.append(artifact)
        self.updated_at = _now()

    def set_coordinator_plan(self, plan: CoordinatorPlan | None) -> None:
        self.coordinator_plan = plan
        self.updated_at = _now()

    @classmethod
    def from_dict(cls, payload: dict) -> "WorkOrder":
        steps = [TaskStep(**item) for item in payload.get("steps", [])]
        artifacts = [ArtifactRef(**item) for item in payload.get("artifacts", [])]
        coordinator_plan_payload = payload.get("coordinator_plan")
        return cls(
            work_order_id=payload["work_order_id"],
            employee_id=payload["employee_id"],
            input_text=payload["input_text"],
            tenant=payload.get("tenant"),
            config_snapshot_id=payload.get("config_snapshot_id"),
            budget_tokens=payload["budget_tokens"],
            execution_mode=payload.get("execution_mode", ExecutionMode.SINGLE.value),
            coordinator_participants=list(payload.get("coordinator_participants", [])),
            coordinator_plan=CoordinatorPlan(**coordinator_plan_payload) if coordinator_plan_payload else None,
            status=payload.get("status", WorkOrderStatus.PENDING.value),
            created_at=payload.get("created_at", _now()),
            updated_at=payload.get("updated_at", _now()),
            steps=steps,
            artifacts=artifacts,
            last_session_id=payload.get("last_session_id"),
            last_approval_id=payload.get("last_approval_id"),
            output_summary=payload.get("output_summary", ""),
            last_error=payload.get("last_error"),
        )
