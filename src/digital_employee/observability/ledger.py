"""Event ledger service."""

from __future__ import annotations

import json

from digital_employee.contracts.repositories import EventLedgerRepository
from digital_employee.domain.events import LedgerEvent, RunEvent


class EventLedger:
    def __init__(self, repo: EventLedgerRepository, *, tenant: str | None = None) -> None:
        self._repo = repo
        self._tenant = tenant

    def sync_session_events(
        self,
        *,
        session_id: str,
        events: list[RunEvent],
        trace_id: str | None = None,
        request_id: str | None = None,
    ) -> list[LedgerEvent]:
        existing = self._repo.list_for_session(session_id)
        seen = {self._signature(item) for item in existing}
        new_events: list[LedgerEvent] = []
        for event in events:
            ledger_event = LedgerEvent.from_run_event(
                event,
                tenant=self._tenant,
                session_id=session_id,
                trace_id=trace_id,
                request_id=request_id,
            )
            signature = self._signature(ledger_event)
            if signature in seen:
                continue
            seen.add(signature)
            new_events.append(ledger_event)
        if new_events:
            self._repo.append_all(new_events)
            existing.extend(new_events)
        return existing

    def list_for_session(self, session_id: str) -> list[LedgerEvent]:
        return self._repo.list_for_session(session_id)

    def list_for_work_order(self, work_order_id: str) -> list[LedgerEvent]:
        return self._repo.list_for_work_order(work_order_id)

    def _signature(self, event: LedgerEvent) -> str:
        return json.dumps(
            {
                "event_type": event.event_type,
                "work_order_id": event.work_order_id,
                "session_id": event.session_id,
                "turn_index": event.turn_index,
                "payload": event.payload,
                "created_at": event.created_at,
            },
            sort_keys=True,
            ensure_ascii=True,
        )
