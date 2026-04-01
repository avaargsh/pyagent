"""Projection services built from append-only events."""

from __future__ import annotations

from digital_employee.contracts.repositories import SessionProjectionRepository
from digital_employee.domain.session import SessionProjection, SessionRecord, build_coordination_snapshot


class ProjectionStore:
    def __init__(self, session_repo: SessionProjectionRepository) -> None:
        self._session_repo = session_repo

    def sync_session(self, session, ledger_events) -> SessionProjection:
        projection = SessionProjection.from_session(
            session,
            event_count=len(ledger_events),
            last_event_at=ledger_events[-1].created_at if ledger_events else session.updated_at,
            coordination=build_coordination_snapshot(session.metadata, ledger_events),
        )
        return self._session_repo.save(projection)

    def get_session(self, session_id: str) -> SessionProjection | None:
        return self._session_repo.get(session_id)

    def list_sessions(self) -> list[SessionProjection]:
        return self._session_repo.list_all()

    def as_session_record(self, projection: SessionProjection, ledger_events) -> SessionRecord:
        return SessionRecord(
            session=projection.to_session(),
            events=[event.to_run_event() for event in ledger_events],
        )
