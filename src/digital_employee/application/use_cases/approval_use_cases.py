"""Approval use cases."""

from __future__ import annotations

from dataclasses import asdict

from digital_employee.application.dto.approvals import ApprovalView
from digital_employee.application.dto.common import CommandResult
from digital_employee.application.services.deps import Deps
from digital_employee.application.services.session_observability import load_session_record, persist_session_record
from digital_employee.domain.errors import DigitalEmployeeError, NotFoundError
from digital_employee.domain.events import RunEvent
from digital_employee.domain.session import SessionRecord


def list_approvals(deps: Deps, *, status: str | None = None) -> CommandResult:
    approvals = deps.approval_repo.list_all()
    if status is not None:
        approvals = [item for item in approvals if item.status == status]
    views = [_to_view(item) for item in approvals]
    data = {"approvals": [asdict(item) for item in views]}
    human_lines = [f"{len(views)} approvals"]
    human_lines.extend(
        f"- {item.approval_id}: {item.status} [{item.tool_name}] work-order={item.work_order_id or 'none'}"
        for item in views
    )
    return CommandResult(command="approval list", data=data, human_lines=human_lines)


def get_approval(deps: Deps, approval_id: str) -> CommandResult:
    approval = deps.approval_repo.get(approval_id)
    if approval is None:
        raise NotFoundError("approval", approval_id)
    view = _to_view(approval)
    data = {"approval": asdict(view)}
    human_lines = [
        f"Approval {view.approval_id}",
        f"Status: {view.status}",
        f"Work order: {view.work_order_id or 'none'}",
        f"Session: {view.session_id}",
        f"Employee: {view.employee_id}",
        f"Tool: {view.tool_name}",
        f"Reason: {view.requested_reason}",
    ]
    if view.decision_reason:
        human_lines.append(f"Decision reason: {view.decision_reason}")
    return CommandResult(command="approval get", data=data, human_lines=human_lines)


def decide_approval(deps: Deps, approval_id: str, *, decision: str, reason: str) -> CommandResult:
    approval = deps.approval_repo.get(approval_id)
    if approval is None:
        raise NotFoundError("approval", approval_id)
    if approval.status != "pending":
        raise DigitalEmployeeError(
            message=f"approval {approval_id} cannot be updated: status is {approval.status}",
            error_type="approval_conflict",
            exit_code=7,
            hint=f"run 'dectl approval get {approval_id}' to inspect the existing decision",
        )

    if decision == "approve":
        approval.approve(reason)
    else:
        approval.reject(reason)
    deps.approval_repo.save(approval)

    _append_approval_event(deps, approval)
    _apply_work_order_side_effects(deps, approval)

    view = _to_view(approval)
    data = {"approval": asdict(view)}
    human_lines = [
        f"Updated approval {approval.approval_id}",
        f"Status: {approval.status}",
        f"Work order: {approval.work_order_id or 'none'}",
    ]
    return CommandResult(command="approval decide", data=data, human_lines=human_lines)


def _append_approval_event(deps: Deps, approval) -> None:
    record = load_session_record(deps, approval.session_id)
    if record is None:
        return
    events = list(record.events)
    events.append(
        RunEvent(
            event_type=f"approval.{approval.status}",
            work_order_id=approval.work_order_id,
            payload={
                "approval_id": approval.approval_id,
                "tool_name": approval.tool_name,
                "decision": approval.decision,
                "reason": approval.decision_reason,
            },
        )
    )
    session = record.session
    if approval.status == "rejected":
        session.close(
            current_stage="failed",
            turns=session.turns,
            budget_used=session.budget_used,
            budget_remaining=session.budget_remaining,
            metadata={"last_error": f"approval {approval.approval_id} was rejected"},
        )
    persist_session_record(deps, SessionRecord(session=session, events=events))


def _apply_work_order_side_effects(deps: Deps, approval) -> None:
    if approval.work_order_id is None:
        return
    work_order = deps.work_order_repo.get(approval.work_order_id)
    if work_order is None:
        return
    work_order.last_approval_id = approval.approval_id
    if approval.status == "rejected":
        work_order.mark_failed(
            f"approval {approval.approval_id} was rejected: {approval.decision_reason}",
            session_id=approval.session_id,
        )
    deps.work_order_repo.save(work_order)


def _to_view(approval) -> ApprovalView:
    return ApprovalView(
        approval_id=approval.approval_id,
        work_order_id=approval.work_order_id,
        session_id=approval.session_id,
        employee_id=approval.employee_id,
        tool_name=approval.tool_name,
        tool_payload=dict(approval.tool_payload),
        approval_policy=approval.approval_policy,
        requested_reason=approval.requested_reason,
        status=approval.status,
        created_at=approval.created_at,
        decided_at=approval.decided_at,
        decision=approval.decision,
        decision_reason=approval.decision_reason,
    )
