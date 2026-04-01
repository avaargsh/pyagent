"""Session models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from secrets import token_hex
from typing import Any

from digital_employee.domain.enums import SessionStatus
from digital_employee.domain.events import RunEvent
from digital_employee.domain.runtime_constraints import (
    COORDINATOR_STARTED_EVENT,
    COORDINATOR_WORKER_SELECTED_EVENT,
    COORDINATION_METADATA_KEYS,
    ExecutionMode,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def generate_session_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"ses_{stamp}_{token_hex(3)}"


@dataclass(slots=True)
class ConversationMessage:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0
    created_at: str = field(default_factory=_now)


@dataclass(slots=True)
class SessionCompactState:
    strategy: str = "none"
    summary: str = ""
    source_message_count: int = 0
    total_tokens: int = 0
    retained_tokens: int = 0


@dataclass(slots=True)
class ConversationSession:
    session_id: str
    work_order_id: str | None
    employee_id: str | None = None
    status: str = SessionStatus.OPEN.value
    started_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    ended_at: str | None = None
    turns: int = 0
    current_stage: str = "created"
    budget_used: int = 0
    budget_remaining: int = 0
    messages: list[ConversationMessage] = field(default_factory=list)
    compact_state: SessionCompactState = field(default_factory=SessionCompactState)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> ConversationMessage:
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=dict(metadata or {}),
            token_estimate=max(len(content.split()), 1) if content else 0,
        )
        self.messages.append(message)
        self.updated_at = _now()
        return message

    def close(
        self,
        *,
        current_stage: str,
        turns: int,
        budget_used: int,
        budget_remaining: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.status = SessionStatus.CLOSED.value
        self.current_stage = current_stage
        self.turns = turns
        self.budget_used = budget_used
        self.budget_remaining = budget_remaining
        self.ended_at = _now()
        self.updated_at = self.ended_at
        if metadata:
            self.metadata.update(metadata)

    def pause(
        self,
        *,
        current_stage: str,
        turns: int,
        budget_used: int,
        budget_remaining: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.status = SessionStatus.PAUSED.value
        self.current_stage = current_stage
        self.turns = turns
        self.budget_used = budget_used
        self.budget_remaining = budget_remaining
        self.updated_at = _now()
        if metadata:
            self.metadata.update(metadata)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ConversationSession":
        messages = [ConversationMessage(**item) for item in payload.get("messages", [])]
        compact_state = SessionCompactState(**payload.get("compact_state", {}))
        return cls(
            session_id=payload["session_id"],
            work_order_id=payload.get("work_order_id"),
            employee_id=payload.get("employee_id"),
            status=payload.get("status", SessionStatus.OPEN.value),
            started_at=payload.get("started_at", _now()),
            updated_at=payload.get("updated_at", _now()),
            ended_at=payload.get("ended_at"),
            turns=payload.get("turns", 0),
            current_stage=payload.get("current_stage", "created"),
            budget_used=payload.get("budget_used", 0),
            budget_remaining=payload.get("budget_remaining", 0),
            messages=messages,
            compact_state=compact_state,
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class SessionRecord:
    session: ConversationSession
    events: list[RunEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session.to_dict(),
            "events": [asdict(event) for event in self.events],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionRecord":
        return cls(
            session=ConversationSession.from_dict(payload["session"]),
            events=[RunEvent(**item) for item in payload.get("events", [])],
        )


def build_coordination_snapshot(metadata: dict[str, Any], events: list[Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if metadata.get("execution_mode") == ExecutionMode.COORDINATED.value or any(
        key in metadata for key in COORDINATION_METADATA_KEYS if key != "dispatch_mode"
    ):
        payload = {
            "execution_mode": metadata.get("execution_mode", ExecutionMode.COORDINATED.value),
            "dispatch_mode": metadata.get("dispatch_mode"),
            "coordinator_employee_id": metadata.get("coordinator_employee_id"),
            "worker_employee_id": metadata.get("worker_employee_id"),
            "participant_ids": list(metadata.get("participant_ids", [])),
            "selection_reason": metadata.get("selection_reason"),
            "required_tools": list(metadata.get("required_tools", [])),
            "matched_terms": list(metadata.get("matched_terms", [])),
        }

    for event in events:
        event_type = getattr(event, "event_type", "")
        event_payload = dict(getattr(event, "payload", {}) or {})
        if event_type == COORDINATOR_STARTED_EVENT:
            if not payload.get("execution_mode"):
                payload["execution_mode"] = ExecutionMode.COORDINATED.value
            if not payload.get("coordinator_employee_id") and event_payload.get("coordinator_employee_id"):
                payload["coordinator_employee_id"] = event_payload.get("coordinator_employee_id")
            if not payload.get("participant_ids") and event_payload.get("participant_ids"):
                payload["participant_ids"] = list(event_payload.get("participant_ids", []))
        elif event_type == COORDINATOR_WORKER_SELECTED_EVENT:
            if not payload.get("execution_mode"):
                payload["execution_mode"] = ExecutionMode.COORDINATED.value
            if not payload.get("coordinator_employee_id") and event_payload.get("coordinator_employee_id"):
                payload["coordinator_employee_id"] = event_payload.get("coordinator_employee_id")
            if not payload.get("worker_employee_id") and event_payload.get("worker_employee_id"):
                payload["worker_employee_id"] = event_payload.get("worker_employee_id")
            if not payload.get("selection_reason") and event_payload.get("selection_reason"):
                payload["selection_reason"] = event_payload.get("selection_reason")
            if not payload.get("required_tools") and event_payload.get("required_tools"):
                payload["required_tools"] = list(event_payload.get("required_tools", []))
            if not payload.get("matched_terms") and event_payload.get("matched_terms"):
                payload["matched_terms"] = list(event_payload.get("matched_terms", []))

    if not payload:
        return {}

    return {
        "execution_mode": payload.get("execution_mode", ExecutionMode.COORDINATED.value),
        "dispatch_mode": payload.get("dispatch_mode"),
        "coordinator_employee_id": payload.get("coordinator_employee_id"),
        "worker_employee_id": payload.get("worker_employee_id"),
        "participant_ids": list(payload.get("participant_ids", [])),
        "selection_reason": payload.get("selection_reason"),
        "required_tools": list(payload.get("required_tools", [])),
        "matched_terms": list(payload.get("matched_terms", [])),
    }


@dataclass(slots=True)
class SessionProjection:
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
    message_count: int
    event_count: int
    last_event_at: str | None
    coordination: dict[str, Any] = field(default_factory=dict)
    compact_state: dict[str, Any] = field(default_factory=dict)
    session_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_session(
        cls,
        session: ConversationSession,
        *,
        event_count: int,
        last_event_at: str | None,
        coordination: dict[str, Any] | None = None,
    ) -> "SessionProjection":
        return cls(
            session_id=session.session_id,
            work_order_id=session.work_order_id,
            employee_id=session.employee_id,
            status=session.status,
            started_at=session.started_at,
            ended_at=session.ended_at,
            turns=session.turns,
            budget_used=session.budget_used,
            budget_remaining=session.budget_remaining,
            current_stage=session.current_stage,
            message_count=len(session.messages),
            event_count=event_count,
            last_event_at=last_event_at,
            coordination=dict(coordination or {}),
            compact_state=asdict(session.compact_state),
            session_data=session.to_dict(),
        )

    def to_session(self) -> ConversationSession:
        return ConversationSession.from_dict(self.session_data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionProjection":
        return cls(
            session_id=payload["session_id"],
            work_order_id=payload.get("work_order_id"),
            employee_id=payload.get("employee_id"),
            status=payload["status"],
            started_at=payload["started_at"],
            ended_at=payload.get("ended_at"),
            turns=payload.get("turns", 0),
            budget_used=payload.get("budget_used", 0),
            budget_remaining=payload.get("budget_remaining", 0),
            current_stage=payload.get("current_stage", "created"),
            message_count=payload.get("message_count", 0),
            event_count=payload.get("event_count", 0),
            last_event_at=payload.get("last_event_at"),
            coordination=dict(payload.get("coordination", {})),
            compact_state=dict(payload.get("compact_state", {})),
            session_data=dict(payload.get("session_data", {})),
        )
