"""Session persistence helpers that keep legacy and new stores in sync."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from digital_employee.domain.events import RunEvent
from digital_employee.domain.runtime_constraints import (
    BACKGROUND_METADATA_KEYS,
    BackgroundState,
    DispatchMode,
    is_terminal_background_state,
    normalize_dispatch_mode,
)
from digital_employee.domain.session import SessionRecord


def persist_session_record(deps, record: SessionRecord) -> SessionRecord:
    deps.session_repo.save(record)
    ledger_events = deps.event_ledger.sync_session_events(
        session_id=record.session.session_id,
        events=record.events,
    )
    deps.projection_store.sync_session(record.session, ledger_events)
    return record


def load_session_record(deps, session_id: str) -> SessionRecord | None:
    projection = deps.projection_store.get_session(session_id)
    if projection is not None:
        ledger_events = deps.event_ledger.list_for_session(session_id)
        return deps.projection_store.as_session_record(projection, ledger_events)
    return deps.session_repo.get(session_id)


def list_session_records(deps) -> list[SessionRecord]:
    projections = deps.projection_store.list_sessions()
    if projections:
        return [
            deps.projection_store.as_session_record(
                projection,
                deps.event_ledger.list_for_session(projection.session_id),
            )
            for projection in projections
        ]
    return deps.session_repo.list_all()


def stamp_background_metadata(
    session,
    *,
    state: str,
    task_id: str | None = None,
    runner_pid: int | None = None,
    log_path: str | None = None,
    lease_timeout_seconds: int | None = None,
    heartbeat_at: str | None = None,
) -> str:
    timestamp = heartbeat_at or datetime.now(UTC).isoformat()
    session.metadata["dispatch_mode"] = DispatchMode.BACKGROUND.value
    session.metadata["background_state"] = state
    session.metadata["background_last_heartbeat_at"] = timestamp
    if state == BackgroundState.QUEUED.value:
        session.metadata["background_started_at"] = timestamp
        session.metadata.pop("background_finished_at", None)
    else:
        session.metadata.setdefault("background_started_at", timestamp)
    if is_terminal_background_state(state):
        session.metadata["background_finished_at"] = timestamp
    else:
        session.metadata.pop("background_finished_at", None)
    if task_id is not None:
        session.metadata["task_id"] = task_id
    if runner_pid is not None:
        session.metadata["runner_pid"] = runner_pid
    if log_path is not None:
        session.metadata["log_path"] = log_path
    if lease_timeout_seconds is not None:
        session.metadata["lease_timeout_seconds"] = lease_timeout_seconds
    session.updated_at = timestamp
    return timestamp


def sync_background_metadata(target_session, source_session) -> None:
    for key in BACKGROUND_METADATA_KEYS:
        if key in source_session.metadata:
            target_session.metadata[key] = source_session.metadata[key]


def build_background_view(session, *, now: datetime | None = None) -> dict[str, Any] | None:
    try:
        dispatch_mode = normalize_dispatch_mode(session.metadata.get("dispatch_mode"))
    except ValueError:
        dispatch_mode = None
    background_state = session.metadata.get("background_state")
    if dispatch_mode != DispatchMode.BACKGROUND and background_state is None:
        return None

    lease_timeout_seconds = _coerce_int(session.metadata.get("lease_timeout_seconds"))
    last_heartbeat_at = session.metadata.get("background_last_heartbeat_at")
    state = str(background_state or "unknown")
    heartbeat_status = "unknown"
    if is_terminal_background_state(state):
        heartbeat_status = "stopped"
    elif last_heartbeat_at and lease_timeout_seconds:
        try:
            heartbeat_at = datetime.fromisoformat(last_heartbeat_at)
        except ValueError:
            heartbeat_status = "unknown"
        else:
            current_time = now or datetime.now(UTC)
            age_seconds = (current_time - heartbeat_at).total_seconds()
            heartbeat_status = "stale" if age_seconds > lease_timeout_seconds else "healthy"

    return {
        "state": state,
        "task_id": session.metadata.get("task_id"),
        "runner_pid": _coerce_int(session.metadata.get("runner_pid")),
        "log_path": session.metadata.get("log_path"),
        "lease_timeout_seconds": lease_timeout_seconds,
        "last_heartbeat_at": last_heartbeat_at,
        "started_at": session.metadata.get("background_started_at"),
        "finished_at": session.metadata.get("background_finished_at"),
        "heartbeat_status": heartbeat_status,
    }


def is_stale_background_view(view: dict[str, Any] | None) -> bool:
    return bool(view and view.get("heartbeat_status") == "stale")


def append_background_heartbeat(
    deps,
    *,
    session_id: str,
    work_order_id: str | None,
    task_id: str,
    runner_pid: int | None,
    lease_timeout_seconds: int,
) -> SessionRecord | None:
    record = load_session_record(deps, session_id)
    if record is None:
        return None
    timestamp = stamp_background_metadata(
        record.session,
        state=BackgroundState.RUNNING.value,
        task_id=task_id,
        runner_pid=runner_pid,
        lease_timeout_seconds=lease_timeout_seconds,
    )
    events = list(record.events)
    events.append(
        RunEvent(
            event_type="session.heartbeat",
            work_order_id=work_order_id,
            payload={
                "session_id": session_id,
                "task_id": task_id,
                "runner_pid": runner_pid,
                "lease_timeout_seconds": lease_timeout_seconds,
            },
            created_at=timestamp,
        )
    )
    return persist_session_record(deps, SessionRecord(session=record.session, events=events))


def _coerce_int(value) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
