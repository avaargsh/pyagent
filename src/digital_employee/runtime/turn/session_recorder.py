"""Event recording and progress publication for turn runs."""

from __future__ import annotations

from digital_employee.domain.events import RunEvent


class SessionRecorder:
    def record_event(
        self,
        events: list[RunEvent],
        *,
        event_type: str,
        work_order_id: str | None,
        payload: dict,
        turn_index: int | None = None,
    ) -> None:
        events.append(
            RunEvent(
                event_type=event_type,
                work_order_id=work_order_id,
                turn_index=turn_index,
                payload=payload,
            )
        )

    def publish_progress(self, session, events: list[RunEvent], progress_callback) -> None:
        if progress_callback is not None:
            progress_callback(session, list(events))
