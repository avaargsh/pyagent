"""Read-only work-order query handlers."""

from __future__ import annotations

from dataclasses import asdict

from digital_employee.application.dto.common import CommandResult
from digital_employee.application.dto.work_orders import CoordinatorPlanView, WorkOrderView
from digital_employee.application.services.deps import Deps
from digital_employee.application.services.session_observability import build_background_view, load_session_record
from digital_employee.application.services.work_order_support import (
    get_required_work_order,
    resolve_work_order_session_record,
)


def get_work_order(deps: Deps, work_order_id: str) -> CommandResult:
    work_order = get_required_work_order(deps, work_order_id)
    session_record = (
        load_session_record(deps, work_order.last_session_id)
        if work_order.last_session_id is not None
        else None
    )
    background = build_background_view(session_record.session) if session_record is not None else None

    view = WorkOrderView(
        work_order_id=work_order.work_order_id,
        employee_id=work_order.employee_id,
        tenant=work_order.tenant,
        config_snapshot_id=work_order.config_snapshot_id,
        execution_mode=work_order.execution_mode,
        coordinator_participants=list(work_order.coordinator_participants),
        coordinator_plan=(
            CoordinatorPlanView(
                worker_employee_id=work_order.coordinator_plan.worker_employee_id,
                selection_reason=work_order.coordinator_plan.selection_reason,
                required_tools=list(work_order.coordinator_plan.required_tools),
                matched_terms=list(work_order.coordinator_plan.matched_terms),
            )
            if work_order.coordinator_plan is not None
            else None
        ),
        status=work_order.status,
        budget_tokens=work_order.budget_tokens,
        input_text=work_order.input_text,
        output_summary=work_order.output_summary,
        last_session_id=work_order.last_session_id,
        last_approval_id=work_order.last_approval_id,
        last_error=work_order.last_error,
        created_at=work_order.created_at,
        updated_at=work_order.updated_at,
    )
    data = {
        "work_order": asdict(view),
        "background": background,
    }
    human_lines = [
        f"Work order {view.work_order_id}",
        f"Employee: {view.employee_id}",
        f"Mode: {view.execution_mode}",
        f"Worker: {view.coordinator_plan.worker_employee_id if view.coordinator_plan else view.employee_id}",
        f"Status: {view.status}",
        f"Budget: {view.budget_tokens}",
        f"Created: {view.created_at}",
        f"Input: {view.input_text}",
    ]
    if background is not None:
        human_lines.append(
            "Background: "
            f"{background['state']} [{background['heartbeat_status']}] "
            f"task={background['task_id'] or 'unknown'}"
        )
    return CommandResult(command="work-order get", data=data, human_lines=human_lines)


def list_work_orders(deps: Deps) -> CommandResult:
    orders = [asdict(item) for item in deps.work_order_repo.list_all()]
    human_lines = [f"{len(orders)} work orders"]
    human_lines.extend(
        f"- {item['work_order_id']}: {item['status']} [{item['employee_id']}]"
        for item in orders
    )
    return CommandResult(command="work-order list", data={"work_orders": orders}, human_lines=human_lines)


def list_work_order_artifacts(deps: Deps, work_order_id: str) -> CommandResult:
    work_order = get_required_work_order(deps, work_order_id)
    artifacts = [asdict(item) for item in work_order.artifacts]
    human_lines = [
        f"Artifacts for {work_order.work_order_id}",
        f"Count: {len(artifacts)}",
    ]
    if artifacts:
        human_lines.extend(
            f"- {item['kind']}: {item['name']} ({item['uri']})"
            for item in artifacts
        )
    else:
        human_lines.append("- none")
    return CommandResult(
        command="work-order artifacts",
        data={
            "work_order_id": work_order.work_order_id,
            "status": work_order.status,
            "session_id": work_order.last_session_id,
            "artifacts": artifacts,
        },
        human_lines=human_lines,
    )


def watch_work_order(deps: Deps, work_order_id: str) -> CommandResult:
    work_order = get_required_work_order(deps, work_order_id)
    record = resolve_work_order_session_record(deps, work_order_id)
    events = [asdict(event) for event in record.events]
    background = build_background_view(record.session)
    human_lines = [
        f"Work-order events for {work_order.work_order_id}",
        f"Session: {record.session.session_id}",
        f"Status: {work_order.status}",
    ]
    if background is not None:
        human_lines.append(
            "Background: "
            f"{background['state']} [{background['heartbeat_status']}] "
            f"task={background['task_id'] or 'unknown'}"
        )
    if events:
        human_lines.extend(f"- {item['created_at']}: {item['event_type']}" for item in events)
    else:
        human_lines.append("- none")
    return CommandResult(
        command="work-order watch",
        data={
            "work_order_id": work_order.work_order_id,
            "status": work_order.status,
            "session_id": record.session.session_id,
            "background": background,
            "events": events,
        },
        human_lines=human_lines,
    )
