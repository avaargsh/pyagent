"""Doctor diagnostics use cases."""

from __future__ import annotations

from digital_employee.application.dto.common import CommandResult
from digital_employee.application.services.deps import Deps
from digital_employee.application.services.session_observability import (
    build_background_view,
    is_stale_background_view,
    list_session_records,
)
from digital_employee.domain.runtime_constraints import is_terminal_background_state


def run_doctor(deps: Deps) -> CommandResult:
    stale_sessions: list[dict] = []
    background_sessions = 0
    active_background_sessions = 0

    for record in list_session_records(deps):
        background = build_background_view(record.session)
        if background is None:
            continue
        background_sessions += 1
        if not is_terminal_background_state(background["state"]):
            active_background_sessions += 1
        if not is_stale_background_view(background):
            continue
        stale_sessions.append(
            {
                "session_id": record.session.session_id,
                "work_order_id": record.session.work_order_id,
                "employee_id": record.session.employee_id,
                "status": record.session.status,
                "current_stage": record.session.current_stage,
                "background": background,
            }
        )

    status = "ok" if not stale_sessions else "warn"
    message = "no stale background sessions detected"
    if stale_sessions:
        message = f"detected {len(stale_sessions)} stale background session(s)"

    data = {
        "summary": {
            "background_sessions": background_sessions,
            "active_background_sessions": active_background_sessions,
            "stale_background_sessions": len(stale_sessions),
        },
        "checks": [
            {
                "name": "background_leases",
                "status": status,
                "message": message,
            }
        ],
        "stale_sessions": stale_sessions,
    }
    human_lines = [
        "Doctor summary",
        f"Background sessions: {background_sessions}",
        f"Active background sessions: {active_background_sessions}",
        f"Stale background sessions: {len(stale_sessions)}",
    ]
    if stale_sessions:
        human_lines.extend(
            (
                f"- {item['session_id']}: work-order={item['work_order_id'] or 'none'} "
                f"state={item['background']['state']} "
                f"heartbeat={item['background']['heartbeat_status']} "
                f"last={item['background']['last_heartbeat_at'] or 'unknown'}"
            )
            for item in stale_sessions
        )
    return CommandResult(command="doctor", data=data, human_lines=human_lines)
