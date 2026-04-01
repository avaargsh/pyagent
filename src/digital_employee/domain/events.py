"""Event models."""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass, field
from secrets import token_hex
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _event_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"evt_{stamp}_{token_hex(3)}"


@dataclass(slots=True)
class RunEvent:
    event_type: str
    work_order_id: str | None = None
    turn_index: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)


@dataclass(slots=True)
class LedgerEvent:
    event_id: str = field(default_factory=_event_id)
    event_type: str = ""
    tenant: str | None = None
    work_order_id: str | None = None
    session_id: str | None = None
    turn_index: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    trace_id: str | None = None
    request_id: str | None = None

    @classmethod
    def from_run_event(
        cls,
        event: RunEvent,
        *,
        tenant: str | None,
        session_id: str,
        trace_id: str | None = None,
        request_id: str | None = None,
    ) -> "LedgerEvent":
        return cls(
            event_type=event.event_type,
            tenant=tenant,
            work_order_id=event.work_order_id,
            session_id=session_id,
            turn_index=event.turn_index,
            payload=dict(event.payload),
            created_at=event.created_at,
            trace_id=trace_id,
            request_id=request_id,
        )

    def to_run_event(self) -> RunEvent:
        return RunEvent(
            event_type=self.event_type,
            work_order_id=self.work_order_id,
            turn_index=self.turn_index,
            payload=dict(self.payload),
            created_at=self.created_at,
        )
