"""Approval models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from secrets import token_hex
from typing import Any

from digital_employee.domain.enums import ApprovalStatus


def _now() -> str:
    return datetime.now(UTC).isoformat()


def generate_approval_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"ap_{stamp}_{token_hex(3)}"


@dataclass(slots=True)
class ApprovalRequest:
    approval_id: str
    work_order_id: str | None
    session_id: str
    employee_id: str
    tool_name: str
    tool_payload: dict[str, Any] = field(default_factory=dict)
    approval_policy: str = ""
    requested_reason: str = ""
    status: str = ApprovalStatus.PENDING.value
    created_at: str = field(default_factory=_now)
    decided_at: str | None = None
    decision: str | None = None
    decision_reason: str | None = None

    @classmethod
    def create_new(
        cls,
        *,
        work_order_id: str | None,
        session_id: str,
        employee_id: str,
        tool_name: str,
        tool_payload: dict[str, Any],
        approval_policy: str,
        requested_reason: str,
    ) -> "ApprovalRequest":
        return cls(
            approval_id=generate_approval_id(),
            work_order_id=work_order_id,
            session_id=session_id,
            employee_id=employee_id,
            tool_name=tool_name,
            tool_payload=dict(tool_payload),
            approval_policy=approval_policy,
            requested_reason=requested_reason,
        )

    def approve(self, reason: str) -> None:
        self.status = ApprovalStatus.APPROVED.value
        self.decision = "approve"
        self.decision_reason = reason
        self.decided_at = _now()

    def reject(self, reason: str) -> None:
        self.status = ApprovalStatus.REJECTED.value
        self.decision = "reject"
        self.decision_reason = reason
        self.decided_at = _now()

    def expire(self, reason: str) -> None:
        self.status = ApprovalStatus.EXPIRED.value
        self.decision = "expire"
        self.decision_reason = reason
        self.decided_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ApprovalRequest":
        return cls(
            approval_id=payload["approval_id"],
            work_order_id=payload.get("work_order_id"),
            session_id=payload["session_id"],
            employee_id=payload["employee_id"],
            tool_name=payload["tool_name"],
            tool_payload=dict(payload.get("tool_payload", {})),
            approval_policy=payload.get("approval_policy", ""),
            requested_reason=payload.get("requested_reason", ""),
            status=payload.get("status", ApprovalStatus.PENDING.value),
            created_at=payload.get("created_at", _now()),
            decided_at=payload.get("decided_at"),
            decision=payload.get("decision"),
            decision_reason=payload.get("decision_reason"),
        )


@dataclass(slots=True)
class ApprovalDecision:
    approval_id: str
    decision: str
    reason: str
