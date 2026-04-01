"""State-changing work-order command handlers."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import UTC, datetime

from digital_employee.application.dto.common import CommandResult
from digital_employee.application.dto.work_orders import CreateWorkOrderRequest, RunWorkOrderView
from digital_employee.application.services.deps import Deps
from digital_employee.application.services.session_observability import (
    append_background_heartbeat,
    build_background_view,
    is_stale_background_view,
    load_session_record,
    persist_session_record,
    stamp_background_metadata,
    sync_background_metadata,
)
from digital_employee.application.services.work_order_support import (
    ensure_can_start,
    get_latest_work_order_approval,
    get_required_work_order,
    merge_events,
    pause_for_approval,
    resolve_work_order_session_record,
    spawn_background_runner,
    terminate_background_runner,
    write_summary_artifact,
)
from digital_employee.domain.errors import ApprovalRequiredError, DigitalEmployeeError, NotFoundError
from digital_employee.domain.events import RunEvent
from digital_employee.domain.enums import SessionStatus
from digital_employee.domain.runtime_constraints import (
    BackgroundState,
    DispatchMode,
    ExecutionMode,
    normalize_participant_ids,
)
from digital_employee.domain.session import ConversationSession, SessionRecord, generate_session_id
from digital_employee.domain.work_order import CoordinatorPlan, WorkOrder
from digital_employee.runtime.task_supervisor import new_task_id

_BACKGROUND_HEARTBEAT_INTERVAL_SECONDS = 0.1
_DEFAULT_RECLAIM_REASON = "background lease expired; work order reclaimed by the operator"


def create_work_order(
    deps: Deps,
    employee_id: str,
    input_text: str,
    budget_tokens: int | None,
    *,
    coordinated: bool = False,
    participant_ids: list[str] | None = None,
) -> CommandResult:
    profile = deps.employee_registry.get_profile(employee_id)
    if profile is None:
        raise NotFoundError("employee", employee_id)

    budget = budget_tokens or deps.config.system.runtime.default_budget_tokens
    normalized_participants = normalize_participant_ids(participant_ids)
    execution_mode = ExecutionMode.COORDINATED.value if coordinated else ExecutionMode.SINGLE.value
    if execution_mode == ExecutionMode.COORDINATED.value and not normalized_participants:
        normalized_participants = [employee_id]
    coordinator_plan = None
    if execution_mode == ExecutionMode.COORDINATED.value:
        coordinator_plan = deps.coordinator_runtime.select_plan(
            coordinator_employee_id=employee_id,
            participant_ids=normalized_participants,
            prompt=input_text,
        )
    request = CreateWorkOrderRequest(
        employee_id=employee_id,
        input_text=input_text,
        budget_tokens=budget,
        tenant=deps.config.tenant,
        config_snapshot_id=deps.config_version,
        execution_mode=execution_mode,
        coordinator_participants=normalized_participants,
    )
    work_order = WorkOrder.create_new(
        employee_id=request.employee_id,
        input_text=request.input_text,
        budget_tokens=request.budget_tokens,
        tenant=request.tenant,
        config_snapshot_id=request.config_snapshot_id,
        execution_mode=request.execution_mode,
        coordinator_participants=request.coordinator_participants,
        coordinator_plan=coordinator_plan,
    )
    deps.work_order_repo.create(work_order)
    data = {"work_order": asdict(work_order)}
    human_lines = [
        f"Created work order {work_order.work_order_id}",
        f"Status: {work_order.status}",
        f"Next: dectl work-order get {work_order.work_order_id}",
    ]
    return CommandResult(command="work-order create", data=data, human_lines=human_lines)


async def run_work_order(deps: Deps, work_order_id: str) -> CommandResult:
    work_order = get_required_work_order(deps, work_order_id)
    ensure_can_start(work_order)
    runtime_cell = _resolve_runtime_cell(deps, work_order)

    work_order.mark_running()
    deps.work_order_repo.save(work_order)

    async def _execute():
        return await _run_work_order_turn(deps, work_order, dispatch_mode=DispatchMode.FOREGROUND.value)

    task = runtime_cell.task_supervisor.start(
        name=f"run-{work_order.work_order_id}",
        factory=_execute,
        timeout_seconds=deps.config.system.runtime.background_task_timeout_seconds,
    )
    managed = await runtime_cell.task_supervisor.wait(task.task_id)
    if managed.status != "completed":
        error_message = managed.error or "work order execution failed"
        work_order.mark_failed(error_message)
        deps.work_order_repo.save(work_order)
        raise DigitalEmployeeError(
            message=error_message,
            error_type="work_order_run_failed",
            exit_code=8,
            hint="inspect the work order and session records for details",
        )

    run_result = managed.result
    if run_result.status == "waiting_approval":
        _apply_session_execution_metadata(deps, run_result.session, work_order, dispatch_mode=DispatchMode.FOREGROUND.value)
        return pause_for_approval(deps, work_order, run_result, command_name="work-order run")

    _apply_session_execution_metadata(deps, run_result.session, work_order, dispatch_mode=DispatchMode.FOREGROUND.value)
    artifact = write_summary_artifact(deps, work_order, run_result.output_text, run_result.session_id)
    work_order.add_artifact(artifact)
    work_order.mark_completed(run_result.output_text, session_id=run_result.session_id)
    deps.work_order_repo.save(work_order)
    persist_session_record(deps, SessionRecord(session=run_result.session, events=run_result.events))

    view = RunWorkOrderView(
        work_order_id=work_order.work_order_id,
        session_id=run_result.session_id,
        task_id=managed.task_id,
        status=work_order.status,
        output_summary=run_result.output_text,
        budget_used=run_result.budget_used,
        budget_remaining=run_result.budget_remaining,
    )
    data = {
        "run": asdict(view),
        "artifact": asdict(artifact),
    }
    human_lines = [
        f"Ran work order {work_order.work_order_id}",
        f"Session: {run_result.session_id}",
        f"Task: {managed.task_id}",
        f"Status: {work_order.status}",
        f"Next: dectl session get {run_result.session_id}",
    ]
    return CommandResult(command="work-order run", data=data, human_lines=human_lines)


def start_background_work_order(deps: Deps, work_order_id: str) -> CommandResult:
    work_order = get_required_work_order(deps, work_order_id)
    ensure_can_start(work_order)
    runtime_cell = _resolve_runtime_cell(deps, work_order)

    session_id = generate_session_id()
    task_id = new_task_id()
    lease_timeout_seconds = deps.config.system.runtime.background_task_timeout_seconds
    work_order.mark_running()
    work_order.last_session_id = session_id
    deps.work_order_repo.save(work_order)
    execution_profile = _resolve_execution_profile(deps, work_order)
    session = ConversationSession(
        session_id=session_id,
        work_order_id=work_order.work_order_id,
        employee_id=execution_profile.employee_id,
        status=SessionStatus.OPEN.value,
        current_stage="queued",
        budget_remaining=work_order.budget_tokens,
        metadata={
            "task_id": task_id,
            "dispatch_mode": DispatchMode.BACKGROUND.value,
        },
    )
    _apply_session_execution_metadata(deps, session, work_order, dispatch_mode=DispatchMode.BACKGROUND.value)
    stamp_background_metadata(
        session,
        state=BackgroundState.QUEUED.value,
        task_id=task_id,
        lease_timeout_seconds=lease_timeout_seconds,
    )
    session.add_message("user", work_order.input_text, {"employee_id": execution_profile.employee_id})
    queued_event = RunEvent(
        event_type="session.queued",
        work_order_id=work_order.work_order_id,
        payload={
            "session_id": session_id,
            "task_id": task_id,
            "employee_id": execution_profile.employee_id,
        },
    )
    persist_session_record(deps, SessionRecord(session=session, events=[queued_event]))
    log_path, runner_pid = spawn_background_runner(deps, work_order_id, session_id, task_id)
    stamp_background_metadata(
        session,
        state=BackgroundState.QUEUED.value,
        task_id=task_id,
        runner_pid=runner_pid,
        log_path=str(log_path),
        lease_timeout_seconds=lease_timeout_seconds,
    )
    persist_session_record(deps, SessionRecord(session=session, events=[queued_event]))

    view = RunWorkOrderView(
        work_order_id=work_order.work_order_id,
        session_id=session_id,
        task_id=task_id,
        status=work_order.status,
        output_summary="",
        budget_used=0,
        budget_remaining=work_order.budget_tokens,
    )
    data = {
        "run": asdict(view),
        "mode": DispatchMode.BACKGROUND.value,
        "log_path": str(log_path),
    }
    human_lines = [
        f"Queued work order {work_order.work_order_id}",
        f"Session: {session_id}",
        f"Task: {task_id}",
        f"Next: dectl work-order watch {work_order.work_order_id} --follow --jsonl",
    ]
    return CommandResult(command="work-order run", data=data, human_lines=human_lines)


async def execute_work_order_task(
    deps: Deps,
    work_order_id: str,
    *,
    session_id: str,
    task_id: str,
) -> CommandResult:
    work_order = get_required_work_order(deps, work_order_id)

    existing = load_session_record(deps, session_id)
    session = existing.session if existing is not None else ConversationSession(
        session_id=session_id,
        work_order_id=work_order.work_order_id,
        employee_id=_resolve_execution_profile(deps, work_order).employee_id,
    )
    existing_events = list(existing.events) if existing is not None else []
    runner_pid = _coerce_int(session.metadata.get("runner_pid"))
    lease_timeout_seconds = deps.config.system.runtime.background_task_timeout_seconds
    session.metadata["task_id"] = task_id
    _apply_session_execution_metadata(deps, session, work_order, dispatch_mode=DispatchMode.BACKGROUND.value)
    stamp_background_metadata(
        session,
        state=BackgroundState.RUNNING.value,
        task_id=task_id,
        runner_pid=runner_pid,
        lease_timeout_seconds=lease_timeout_seconds,
    )
    persist_session_record(deps, SessionRecord(session=session, events=existing_events))

    def _progress_callback(updated_session: ConversationSession, updated_events: list[RunEvent]) -> None:
        current_record = load_session_record(deps, session_id)
        if current_record is not None:
            sync_background_metadata(updated_session, current_record.session)
            current_events = list(current_record.events)
        else:
            current_events = []
            stamp_background_metadata(
                updated_session,
                state=BackgroundState.RUNNING.value,
                task_id=task_id,
                runner_pid=runner_pid,
                lease_timeout_seconds=lease_timeout_seconds,
            )
        persist_session_record(
            deps,
            SessionRecord(session=updated_session, events=merge_events(current_events, updated_events)),
        )

    heartbeat_stop = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        _background_heartbeat_loop(
            deps,
            session_id=session_id,
            work_order_id=work_order.work_order_id,
            task_id=task_id,
            runner_pid=runner_pid,
            lease_timeout_seconds=lease_timeout_seconds,
            interval_seconds=_BACKGROUND_HEARTBEAT_INTERVAL_SECONDS,
            stop_event=heartbeat_stop,
        )
    )

    try:
        run_result = await _run_work_order_turn(
            deps,
            work_order,
            session=session,
            progress_callback=_progress_callback,
            dispatch_mode=DispatchMode.BACKGROUND.value,
        )
    except Exception as error:
        await _stop_background_heartbeat(heartbeat_task, heartbeat_stop)
        failed_record = load_session_record(deps, session_id)
        failed_session = failed_record.session if failed_record is not None else session
        failed_events = list(failed_record.events) if failed_record is not None else []
        if failed_record is not None:
            sync_background_metadata(failed_session, failed_record.session)
        failed_events.append(
            RunEvent(
                event_type="turn.failed",
                work_order_id=work_order.work_order_id,
                payload={
                    "session_id": session_id,
                    "task_id": task_id,
                    "error": str(error),
                },
            )
        )
        failed_session.status = SessionStatus.CLOSED.value
        failed_session.current_stage = "failed"
        failed_session.ended_at = datetime.now(UTC).isoformat()
        failed_session.updated_at = failed_session.ended_at
        failed_session.metadata["last_error"] = str(error)
        stamp_background_metadata(
            failed_session,
            state=BackgroundState.FAILED.value,
            task_id=task_id,
            runner_pid=runner_pid,
            lease_timeout_seconds=lease_timeout_seconds,
        )
        persist_session_record(deps, SessionRecord(session=failed_session, events=failed_events))
        work_order.mark_failed(str(error), session_id=session_id)
        deps.work_order_repo.save(work_order)
        raise

    await _stop_background_heartbeat(heartbeat_task, heartbeat_stop)
    current_record = load_session_record(deps, session_id)
    current_events = list(current_record.events) if current_record is not None else []
    if current_record is not None:
        sync_background_metadata(run_result.session, current_record.session)
    combined_events = merge_events(current_events, run_result.events)
    if run_result.status == "waiting_approval":
        _apply_session_execution_metadata(deps, run_result.session, work_order, dispatch_mode=DispatchMode.BACKGROUND.value)
        stamp_background_metadata(
            run_result.session,
            state=BackgroundState.WAITING_APPROVAL.value,
            task_id=task_id,
            runner_pid=runner_pid,
            lease_timeout_seconds=lease_timeout_seconds,
        )
        persist_session_record(deps, SessionRecord(session=run_result.session, events=combined_events))
        work_order.mark_waiting_approval(run_result.approval_id or "", session_id=run_result.session_id)
        deps.work_order_repo.save(work_order)
        return CommandResult(
            command="work-order _execute",
            data={
                "session_id": run_result.session_id,
                "task_id": task_id,
                "status": work_order.status,
                "approval_id": run_result.approval_id,
            },
            human_lines=[f"Paused work order {work_order_id} for approval {run_result.approval_id}"],
        )

    _apply_session_execution_metadata(deps, run_result.session, work_order, dispatch_mode=DispatchMode.BACKGROUND.value)
    artifact = write_summary_artifact(deps, work_order, run_result.output_text, run_result.session_id)
    work_order.add_artifact(artifact)
    work_order.mark_completed(run_result.output_text, session_id=run_result.session_id)
    deps.work_order_repo.save(work_order)
    stamp_background_metadata(
        run_result.session,
        state=BackgroundState.COMPLETED.value,
        task_id=task_id,
        runner_pid=runner_pid,
        lease_timeout_seconds=lease_timeout_seconds,
    )
    persist_session_record(deps, SessionRecord(session=run_result.session, events=combined_events))
    return CommandResult(
        command="work-order _execute",
        data={
            "session_id": run_result.session_id,
            "task_id": task_id,
            "artifact": asdict(artifact),
        },
        human_lines=[f"Executed work order {work_order_id} in background session {run_result.session_id}"],
    )


def cancel_work_order(deps: Deps, work_order_id: str) -> CommandResult:
    work_order = get_required_work_order(deps, work_order_id)
    if work_order.status not in {"running", "waiting_approval"}:
        raise DigitalEmployeeError(
            message=f"work order {work_order.work_order_id} cannot cancel: status is {work_order.status}",
            error_type="work_order_cancel_invalid",
            exit_code=7,
            hint=f"run 'dectl work-order get {work_order.work_order_id}' to inspect the current state",
        )

    record = resolve_work_order_session_record(deps, work_order.work_order_id)
    runner_terminated = work_order.status == "running" and terminate_background_runner(record)
    expired_approval_id = None
    approval = get_latest_work_order_approval(deps, work_order.work_order_id)
    if approval is not None and approval.status == "pending":
        approval.expire("work order was cancelled by the operator")
        deps.approval_repo.save(approval)
        expired_approval_id = approval.approval_id

    events = list(record.events)
    if expired_approval_id is not None:
        events.append(
            RunEvent(
                event_type="approval.expired",
                work_order_id=work_order.work_order_id,
                payload={
                    "approval_id": expired_approval_id,
                    "reason": "work order was cancelled by the operator",
                },
            )
        )
    events.append(
        RunEvent(
            event_type="work-order.cancelled",
            work_order_id=work_order.work_order_id,
            payload={
                "session_id": record.session.session_id,
                "runner_terminated": runner_terminated,
                "approval_id": expired_approval_id,
            },
        )
    )
    record.session.close(
        current_stage="cancelled",
        turns=record.session.turns,
        budget_used=record.session.budget_used,
        budget_remaining=record.session.budget_remaining,
        metadata={
            "cancelled": True,
            "runner_terminated": runner_terminated,
        },
    )
    if record.session.metadata.get("background_state") is not None or record.session.metadata.get("dispatch_mode") == DispatchMode.BACKGROUND.value:
        stamp_background_metadata(
            record.session,
            state=BackgroundState.CANCELLED.value,
            task_id=record.session.metadata.get("task_id"),
            runner_pid=_coerce_int(record.session.metadata.get("runner_pid")),
            lease_timeout_seconds=_coerce_int(record.session.metadata.get("lease_timeout_seconds")),
        )
    persist_session_record(deps, SessionRecord(session=record.session, events=events))
    work_order.mark_cancelled(
        session_id=record.session.session_id,
        reason="work order was cancelled by the operator",
    )
    deps.work_order_repo.save(work_order)

    data = {
        "work_order_id": work_order.work_order_id,
        "status": work_order.status,
        "session_id": record.session.session_id,
        "runner_terminated": runner_terminated,
        "approval_id": expired_approval_id,
    }
    human_lines = [
        f"Cancelled work order {work_order.work_order_id}",
        f"Status: {work_order.status}",
        f"Session: {record.session.session_id}",
    ]
    if expired_approval_id is not None:
        human_lines.append(f"Approval: {expired_approval_id} expired")
    return CommandResult(command="work-order cancel", data=data, human_lines=human_lines)


def reclaim_work_order(deps: Deps, work_order_id: str, *, reason: str | None = None) -> CommandResult:
    work_order = get_required_work_order(deps, work_order_id)
    record = resolve_work_order_session_record(deps, work_order.work_order_id)
    background = build_background_view(record.session)
    if not is_stale_background_view(background):
        raise DigitalEmployeeError(
            message=(
                f"work order {work_order.work_order_id} cannot reclaim: "
                "latest session is not a stale background execution"
            ),
            error_type="work_order_reclaim_invalid",
            exit_code=7,
            hint=f"run 'dectl work-order get {work_order.work_order_id}' to inspect the latest background state",
        )

    reclaim_reason = (reason or _DEFAULT_RECLAIM_REASON).strip()
    runner_terminated = terminate_background_runner(record)
    expired_approval_id = None
    approval = get_latest_work_order_approval(deps, work_order.work_order_id)
    if approval is not None and approval.status == "pending":
        approval.expire(reclaim_reason)
        deps.approval_repo.save(approval)
        expired_approval_id = approval.approval_id

    events = list(record.events)
    if expired_approval_id is not None:
        events.append(
            RunEvent(
                event_type="approval.expired",
                work_order_id=work_order.work_order_id,
                payload={
                    "approval_id": expired_approval_id,
                    "reason": reclaim_reason,
                },
            )
        )
    events.append(
        RunEvent(
            event_type="work-order.reclaimed",
            work_order_id=work_order.work_order_id,
            payload={
                "session_id": record.session.session_id,
                "reason": reclaim_reason,
                "runner_terminated": runner_terminated,
                "approval_id": expired_approval_id,
                "previous_status": work_order.status,
            },
        )
    )
    record.session.close(
        current_stage="reclaimed",
        turns=record.session.turns,
        budget_used=record.session.budget_used,
        budget_remaining=record.session.budget_remaining,
        metadata={
            "reclaimed": True,
            "runner_terminated": runner_terminated,
            "last_error": reclaim_reason,
        },
    )
    stamp_background_metadata(
        record.session,
        state=BackgroundState.FAILED.value,
        task_id=record.session.metadata.get("task_id"),
        runner_pid=_coerce_int(record.session.metadata.get("runner_pid")),
        lease_timeout_seconds=_coerce_int(record.session.metadata.get("lease_timeout_seconds")),
    )
    persist_session_record(deps, SessionRecord(session=record.session, events=events))
    work_order.mark_failed(reclaim_reason, session_id=record.session.session_id)
    deps.work_order_repo.save(work_order)

    data = {
        "work_order_id": work_order.work_order_id,
        "status": work_order.status,
        "session_id": record.session.session_id,
        "reason": reclaim_reason,
        "runner_terminated": runner_terminated,
        "approval_id": expired_approval_id,
    }
    human_lines = [
        f"Reclaimed work order {work_order.work_order_id}",
        f"Status: {work_order.status}",
        f"Session: {record.session.session_id}",
        f"Reason: {reclaim_reason}",
    ]
    if expired_approval_id is not None:
        human_lines.append(f"Approval: {expired_approval_id} expired")
    return CommandResult(command="work-order reclaim", data=data, human_lines=human_lines)


async def resume_work_order(deps: Deps, work_order_id: str) -> CommandResult:
    work_order, runtime_cell, record = _prepare_resume_execution(deps, work_order_id)
    base_events = list(record.events)
    work_order.mark_running()
    deps.work_order_repo.save(work_order)

    def _progress_callback(updated_session: ConversationSession, updated_events: list[RunEvent]) -> None:
        persist_session_record(
            deps,
            SessionRecord(session=updated_session, events=merge_events(base_events, updated_events)),
        )

    async def _execute():
        return await _run_work_order_turn(
            deps,
            work_order,
            session=record.session,
            progress_callback=_progress_callback,
            dispatch_mode=DispatchMode.FOREGROUND.value,
        )

    task = runtime_cell.task_supervisor.start(
        name=f"resume-{work_order.work_order_id}",
        factory=_execute,
        timeout_seconds=deps.config.system.runtime.background_task_timeout_seconds,
    )
    managed = await runtime_cell.task_supervisor.wait(task.task_id)
    if managed.status != "completed":
        error_message = managed.error or "work order resume failed"
        work_order.mark_failed(error_message, session_id=record.session.session_id)
        deps.work_order_repo.save(work_order)
        raise DigitalEmployeeError(
            message=error_message,
            error_type="work_order_resume_failed",
            exit_code=8,
            hint="inspect the work order and session records for details",
        )

    run_result = managed.result
    combined_events = merge_events(base_events, run_result.events)
    if run_result.status == "waiting_approval":
        _apply_session_execution_metadata(deps, run_result.session, work_order, dispatch_mode=DispatchMode.FOREGROUND.value)
        persist_session_record(deps, SessionRecord(session=run_result.session, events=combined_events))
        return pause_for_approval(
            deps,
            work_order,
            run_result,
            command_name="work-order resume",
            events=combined_events,
        )

    _apply_session_execution_metadata(deps, run_result.session, work_order, dispatch_mode=DispatchMode.FOREGROUND.value)
    artifact = write_summary_artifact(deps, work_order, run_result.output_text, run_result.session_id)
    work_order.add_artifact(artifact)
    work_order.mark_completed(run_result.output_text, session_id=run_result.session_id)
    deps.work_order_repo.save(work_order)
    persist_session_record(deps, SessionRecord(session=run_result.session, events=combined_events))

    view = RunWorkOrderView(
        work_order_id=work_order.work_order_id,
        session_id=run_result.session_id,
        task_id=managed.task_id,
        status=work_order.status,
        output_summary=run_result.output_text,
        budget_used=run_result.budget_used,
        budget_remaining=run_result.budget_remaining,
    )
    return CommandResult(
        command="work-order resume",
        data={
            "run": asdict(view),
            "artifact": asdict(artifact),
        },
        human_lines=[
            f"Resumed work order {work_order.work_order_id}",
            f"Session: {run_result.session_id}",
            f"Task: {managed.task_id}",
            f"Status: {work_order.status}",
        ],
    )


def start_background_resume_work_order(deps: Deps, work_order_id: str) -> CommandResult:
    work_order, _runtime_cell, record = _prepare_resume_execution(deps, work_order_id)
    task_id = new_task_id()
    lease_timeout_seconds = deps.config.system.runtime.background_task_timeout_seconds
    work_order.mark_running()
    deps.work_order_repo.save(work_order)

    session = record.session
    session.status = SessionStatus.OPEN.value
    session.current_stage = "queued"
    session.updated_at = datetime.now(UTC).isoformat()
    session.metadata["task_id"] = task_id
    _apply_session_execution_metadata(deps, session, work_order, dispatch_mode=DispatchMode.BACKGROUND.value)
    session.metadata.pop("cancelled", None)
    session.metadata.pop("runner_terminated", None)
    stamp_background_metadata(
        session,
        state=BackgroundState.QUEUED.value,
        task_id=task_id,
        lease_timeout_seconds=lease_timeout_seconds,
    )
    execution_profile = _resolve_execution_profile(deps, work_order)
    resumed_event = RunEvent(
        event_type="session.resumed",
        work_order_id=work_order.work_order_id,
        payload={
            "session_id": session.session_id,
            "task_id": task_id,
            "employee_id": execution_profile.employee_id,
        },
    )
    events = [*record.events, resumed_event]
    persist_session_record(deps, SessionRecord(session=session, events=events))

    log_path, runner_pid = spawn_background_runner(deps, work_order_id, session.session_id, task_id)
    stamp_background_metadata(
        session,
        state=BackgroundState.QUEUED.value,
        task_id=task_id,
        runner_pid=runner_pid,
        log_path=str(log_path),
        lease_timeout_seconds=lease_timeout_seconds,
    )
    persist_session_record(deps, SessionRecord(session=session, events=events))

    view = RunWorkOrderView(
        work_order_id=work_order.work_order_id,
        session_id=session.session_id,
        task_id=task_id,
        status=work_order.status,
        output_summary="",
        budget_used=session.budget_used,
        budget_remaining=session.budget_remaining,
    )
    return CommandResult(
        command="work-order resume",
        data={
            "run": asdict(view),
            "mode": DispatchMode.BACKGROUND.value,
            "log_path": str(log_path),
        },
        human_lines=[
            f"Queued resumed work order {work_order.work_order_id}",
            f"Session: {session.session_id}",
            f"Task: {task_id}",
            f"Next: dectl work-order watch {work_order.work_order_id} --follow --jsonl",
        ],
    )


def _prepare_resume_execution(deps: Deps, work_order_id: str):
    work_order = get_required_work_order(deps, work_order_id)
    if work_order.status != "waiting_approval":
        raise DigitalEmployeeError(
            message=(
                f"work order {work_order.work_order_id} cannot resume: status is {work_order.status}; "
                "use work-order get to inspect final artifacts"
            ),
            error_type="work_order_resume_invalid",
            exit_code=7,
        )

    approval = get_latest_work_order_approval(deps, work_order.work_order_id)
    if approval is None:
        raise DigitalEmployeeError(
            message=f"work order {work_order.work_order_id} cannot resume: no approval was found",
            error_type="approval_not_found",
            exit_code=7,
            hint=f"run 'dectl approval list' to inspect pending requests for {work_order.work_order_id}",
        )
    if approval.status == "pending":
        raise ApprovalRequiredError(
            approval.approval_id,
            hint=f"run `dectl approval decide {approval.approval_id} --decision approve --reason ...`",
        )
    if approval.status != "approved":
        raise DigitalEmployeeError(
            message=(
                f"work order {work_order.work_order_id} cannot resume: latest approval "
                f"{approval.approval_id} is {approval.status}; use approval get to inspect the decision"
            ),
            error_type="work_order_resume_invalid",
            exit_code=7,
        )

    runtime_cell = _resolve_runtime_cell(deps, work_order)
    record = resolve_work_order_session_record(deps, work_order.work_order_id)
    return work_order, runtime_cell, record


def _resolve_execution_profile(deps: Deps, work_order: WorkOrder):
    if work_order.execution_mode == ExecutionMode.COORDINATED.value:
        coordinator_plan = _ensure_coordinator_plan(deps, work_order)
        execution = deps.coordinator_runtime.resolve_execution(
            coordinator_employee_id=work_order.employee_id,
            participant_ids=work_order.coordinator_participants,
            config_version=work_order.config_snapshot_id,
            prompt=work_order.input_text,
            coordinator_plan=coordinator_plan,
        )
        return execution.worker_profile

    profile = deps.employee_registry.get_profile(work_order.employee_id)
    if profile is None:
        raise NotFoundError("employee", work_order.employee_id)
    return profile


def _resolve_runtime_cell(deps: Deps, work_order: WorkOrder):
    if work_order.execution_mode == ExecutionMode.COORDINATED.value:
        coordinator_plan = _ensure_coordinator_plan(deps, work_order)
        execution = deps.coordinator_runtime.resolve_execution(
            coordinator_employee_id=work_order.employee_id,
            participant_ids=work_order.coordinator_participants,
            config_version=work_order.config_snapshot_id,
            prompt=work_order.input_text,
            coordinator_plan=coordinator_plan,
        )
        return execution.runtime_cell

    profile = _resolve_execution_profile(deps, work_order)
    return deps.runtime_manager.get_for_employee(
        profile.employee_id,
        config_version=work_order.config_snapshot_id,
    )


async def _run_work_order_turn(
    deps: Deps,
    work_order: WorkOrder,
    *,
    session: ConversationSession | None = None,
    progress_callback=None,
    dispatch_mode: str,
):
    if work_order.execution_mode == ExecutionMode.COORDINATED.value:
        if session is not None:
            session.metadata["dispatch_mode"] = dispatch_mode
        return await deps.coordinator_runtime.run(
            work_order=work_order,
            prompt=work_order.input_text,
            budget_tokens=work_order.budget_tokens,
            session=session,
            progress_callback=progress_callback,
        )

    profile = _resolve_execution_profile(deps, work_order)
    runtime_cell = deps.runtime_manager.get_for_employee(
        profile.employee_id,
        config_version=work_order.config_snapshot_id,
    )
    result = await runtime_cell.turn_engine.run(
        profile=profile,
        prompt=work_order.input_text,
        work_order_id=work_order.work_order_id,
        budget_tokens=work_order.budget_tokens,
        session=session,
        progress_callback=progress_callback,
    )
    _apply_session_execution_metadata(deps, result.session, work_order, dispatch_mode=dispatch_mode)
    return result


def _apply_session_execution_metadata(
    deps: Deps,
    session: ConversationSession,
    work_order: WorkOrder,
    *,
    dispatch_mode: str,
) -> None:
    session.metadata["execution_mode"] = work_order.execution_mode
    session.metadata["dispatch_mode"] = dispatch_mode
    if work_order.coordinator_participants:
        session.metadata["participant_ids"] = list(work_order.coordinator_participants)
    if work_order.execution_mode == ExecutionMode.COORDINATED.value:
        coordinator_plan = _ensure_coordinator_plan(deps, work_order)
        session.metadata["coordinator_employee_id"] = work_order.employee_id
        session.metadata["worker_employee_id"] = coordinator_plan.worker_employee_id
        session.metadata["selection_reason"] = coordinator_plan.selection_reason
        session.metadata["required_tools"] = list(coordinator_plan.required_tools)
        session.metadata["matched_terms"] = list(coordinator_plan.matched_terms)


def _ensure_coordinator_plan(deps: Deps, work_order: WorkOrder) -> CoordinatorPlan:
    if work_order.coordinator_plan is not None:
        return work_order.coordinator_plan
    coordinator_plan = deps.coordinator_runtime.select_plan(
        coordinator_employee_id=work_order.employee_id,
        participant_ids=work_order.coordinator_participants,
        prompt=work_order.input_text,
    )
    work_order.set_coordinator_plan(coordinator_plan)
    deps.work_order_repo.save(work_order)
    return coordinator_plan


async def _background_heartbeat_loop(
    deps: Deps,
    *,
    session_id: str,
    work_order_id: str,
    task_id: str,
    runner_pid: int | None,
    lease_timeout_seconds: int,
    interval_seconds: float,
    stop_event: asyncio.Event,
) -> None:
    while True:
        append_background_heartbeat(
            deps,
            session_id=session_id,
            work_order_id=work_order_id,
            task_id=task_id,
            runner_pid=runner_pid,
            lease_timeout_seconds=lease_timeout_seconds,
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            return
        except asyncio.TimeoutError:
            continue


async def _stop_background_heartbeat(task: asyncio.Task[None], stop_event: asyncio.Event) -> None:
    stop_event.set()
    await task


def _coerce_int(value) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
