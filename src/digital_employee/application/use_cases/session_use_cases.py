"""Session use cases."""

from __future__ import annotations

from dataclasses import asdict

from digital_employee.application.dto.common import CommandResult
from digital_employee.application.dto.sessions import CoordinationView, SessionExportView, SessionView
from digital_employee.application.services.deps import Deps
from digital_employee.application.services.session_observability import build_background_view, load_session_record
from digital_employee.domain.errors import NotFoundError
from digital_employee.domain.runtime_constraints import ExecutionMode
from digital_employee.domain.session import build_coordination_snapshot


def list_sessions(
    deps: Deps,
    *,
    work_order_id: str | None = None,
    employee_id: str | None = None,
    status: str | None = None,
) -> CommandResult:
    projections = deps.projection_store.list_sessions()
    if projections:
        sessions = [
            SessionView(
                session_id=projection.session_id,
                work_order_id=projection.work_order_id,
                employee_id=projection.employee_id,
                status=projection.status,
                started_at=projection.started_at,
                ended_at=projection.ended_at,
                turns=projection.turns,
                budget_used=projection.budget_used,
                budget_remaining=projection.budget_remaining,
                current_stage=projection.current_stage,
                coordination=_coordination_view(projection.coordination),
            )
            for projection in projections
            if (work_order_id is None or projection.work_order_id == work_order_id)
            and (employee_id is None or projection.employee_id == employee_id)
            and (status is None or projection.status == status)
        ]
    else:
        records = deps.session_repo.list_all()
        sessions = [
            SessionView(
                session_id=record.session.session_id,
                work_order_id=record.session.work_order_id,
                employee_id=record.session.employee_id,
                status=record.session.status,
                started_at=record.session.started_at,
                ended_at=record.session.ended_at,
                turns=record.session.turns,
                budget_used=record.session.budget_used,
                budget_remaining=record.session.budget_remaining,
                current_stage=record.session.current_stage,
                coordination=_coordination_view(
                    build_coordination_snapshot(record.session.metadata, record.events),
                ),
            )
            for record in records
            if (work_order_id is None or record.session.work_order_id == work_order_id)
            and (employee_id is None or record.session.employee_id == employee_id)
            and (status is None or record.session.status == status)
        ]
    data = {"sessions": [asdict(item) for item in sessions]}
    human_lines = [f"{len(sessions)} sessions"]
    human_lines.extend(
        f"- {item.session_id}: {item.status} [{item.employee_id or 'unknown'}] work-order={item.work_order_id or 'none'}"
        for item in sessions
    )
    return CommandResult(command="session list", data=data, human_lines=human_lines)


def get_session(deps: Deps, session_id: str) -> CommandResult:
    record = load_session_record(deps, session_id)
    if record is None:
        raise NotFoundError("session", session_id)
    view = SessionView(
        session_id=record.session.session_id,
        work_order_id=record.session.work_order_id,
        employee_id=record.session.employee_id,
        status=record.session.status,
        started_at=record.session.started_at,
        ended_at=record.session.ended_at,
        turns=record.session.turns,
        budget_used=record.session.budget_used,
        budget_remaining=record.session.budget_remaining,
        current_stage=record.session.current_stage,
        coordination=_coordination_view(
            build_coordination_snapshot(record.session.metadata, record.events),
        ),
    )
    data = {
        "session": asdict(view),
        "message_count": len(record.session.messages),
        "event_count": len(record.events),
        "compaction": asdict(record.session.compact_state),
        "background": build_background_view(record.session),
    }
    human_lines = [
        f"Session {view.session_id}",
        f"Employee: {view.employee_id or 'unknown'}",
        f"Work order: {view.work_order_id or 'none'}",
        f"Status: {view.status}",
        f"Turns: {view.turns}",
        f"Budget: used={view.budget_used} remaining={view.budget_remaining}",
    ]
    if view.coordination is not None:
        human_lines.append(
            "Coordination: "
            f"{view.coordination.coordinator_employee_id or 'unknown'} -> "
            f"{view.coordination.worker_employee_id or 'unknown'}"
        )
    if data["background"] is not None:
        human_lines.append(
            "Background: "
            f"{data['background']['state']} "
            f"[{data['background']['heartbeat_status']}] "
            f"task={data['background']['task_id'] or 'unknown'}"
        )
    return CommandResult(command="session get", data=data, human_lines=human_lines)


def tail_session(deps: Deps, session_id: str) -> CommandResult:
    record = load_session_record(deps, session_id)
    if record is None:
        raise NotFoundError("session", session_id)
    events = [asdict(event) for event in record.events]
    human_lines = [f"Session events for {session_id}"]
    human_lines.extend(
        f"- {item['created_at']}: {item['event_type']}"
        for item in events
    )
    return CommandResult(command="session tail", data={"events": events}, human_lines=human_lines)


def export_session(deps: Deps, session_id: str) -> CommandResult:
    record = load_session_record(deps, session_id)
    if record is None:
        raise NotFoundError("session", session_id)
    view = SessionExportView(
        session=record.session.to_dict(),
        events=[asdict(event) for event in record.events],
        coordination=_coordination_view(
            build_coordination_snapshot(record.session.metadata, record.events),
        ),
    )
    data = {"export": asdict(view)}
    human_lines = [
        f"Exported session {session_id}",
        f"Messages: {len(record.session.messages)}",
        f"Events: {len(record.events)}",
    ]
    return CommandResult(command="session export", data=data, human_lines=human_lines)


def _coordination_view(payload: dict | None) -> CoordinationView | None:
    if not payload:
        return None
    return CoordinationView(
        execution_mode=str(payload.get("execution_mode", ExecutionMode.COORDINATED.value)),
        dispatch_mode=payload.get("dispatch_mode"),
        coordinator_employee_id=payload.get("coordinator_employee_id"),
        worker_employee_id=payload.get("worker_employee_id"),
        participant_ids=list(payload.get("participant_ids", [])),
        selection_reason=payload.get("selection_reason"),
        required_tools=list(payload.get("required_tools", [])),
        matched_terms=list(payload.get("matched_terms", [])),
    )
