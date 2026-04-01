"""Shared work-order helpers used by commands and queries."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from secrets import token_hex
import signal
import subprocess
import sys

from digital_employee.application.dto.common import CommandResult
from digital_employee.application.dto.work_orders import RunWorkOrderView
from digital_employee.application.services.deps import Deps
from digital_employee.application.services.session_observability import load_session_record, persist_session_record
from digital_employee.domain.artifact import ArtifactRef
from digital_employee.domain.errors import DigitalEmployeeError, NotFoundError
from digital_employee.domain.events import RunEvent
from digital_employee.domain.session import SessionRecord
from digital_employee.domain.work_order import WorkOrder


def artifact_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"artifact_{stamp}_{token_hex(3)}"


def get_required_work_order(deps: Deps, work_order_id: str) -> WorkOrder:
    work_order = deps.work_order_repo.get(work_order_id)
    if work_order is None:
        raise NotFoundError("work order", work_order_id)
    return work_order


def resolve_work_order_session_record(deps: Deps, work_order_id: str) -> SessionRecord:
    work_order = get_required_work_order(deps, work_order_id)
    if work_order.last_session_id:
        record = load_session_record(deps, work_order.last_session_id)
        if record is not None:
            return record

    for projection in deps.projection_store.list_sessions():
        record = deps.projection_store.as_session_record(
            projection,
            deps.event_ledger.list_for_session(projection.session_id),
        )
        if record.session.work_order_id == work_order.work_order_id:
            return record

    for record in deps.session_repo.list_all():
        if record.session.work_order_id == work_order.work_order_id:
            return record

    raise DigitalEmployeeError(
        message=f"work order {work_order.work_order_id} has no session history yet",
        error_type="work_order_session_unavailable",
        exit_code=7,
        hint="run the work order before trying to watch its session events",
    )


def get_latest_work_order_approval(deps: Deps, work_order_id: str):
    for approval in deps.approval_repo.list_all():
        if approval.work_order_id == work_order_id:
            return approval
    return None


def ensure_can_start(work_order: WorkOrder) -> None:
    if work_order.status == "waiting_approval":
        raise DigitalEmployeeError(
            message=(
                f"work order {work_order.work_order_id} cannot run: status is {work_order.status}; "
                "use work-order resume after deciding the approval"
            ),
            error_type="work_order_resume_required",
            exit_code=7,
        )
    if work_order.status in {"running", "completed", "cancelled"}:
        raise DigitalEmployeeError(
            message=f"work order {work_order.work_order_id} cannot run: status is {work_order.status}",
            error_type="work_order_state_invalid",
            exit_code=7,
            hint=f"run 'dectl work-order get {work_order.work_order_id}' to inspect the current state",
        )


def pause_for_approval(
    deps: Deps,
    work_order: WorkOrder,
    run_result,
    *,
    command_name: str,
    events: list[RunEvent] | None = None,
) -> CommandResult:
    work_order.mark_waiting_approval(run_result.approval_id or "", session_id=run_result.session_id)
    deps.work_order_repo.save(work_order)
    persist_session_record(deps, SessionRecord(session=run_result.session, events=events or run_result.events))
    view = RunWorkOrderView(
        work_order_id=work_order.work_order_id,
        session_id=run_result.session_id,
        task_id=run_result.session.metadata.get("task_id", ""),
        status=work_order.status,
        output_summary=run_result.output_text,
        budget_used=run_result.budget_used,
        budget_remaining=run_result.budget_remaining,
    )
    return CommandResult(
        command=command_name,
        data={
            "run": asdict(view),
            "approval": {
                "approval_id": run_result.approval_id,
                "status": work_order.status,
            },
        },
        human_lines=[
            f"Paused work order {work_order.work_order_id}",
            f"Status: {work_order.status}",
            f"Approval: {run_result.approval_id}",
            f"Next: dectl approval decide {run_result.approval_id} --decision approve --reason ...",
        ],
    )


def merge_events(base_events: list[RunEvent], new_events: list[RunEvent]) -> list[RunEvent]:
    merged: list[RunEvent] = []
    seen: set[str] = set()
    for event in [*base_events, *new_events]:
        signature = json.dumps(
            {
                "event_type": event.event_type,
                "work_order_id": event.work_order_id,
                "turn_index": event.turn_index,
                "payload": event.payload,
                "created_at": event.created_at,
            },
            sort_keys=True,
            ensure_ascii=True,
        )
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(event)
    return merged


def write_summary_artifact(deps: Deps, work_order: WorkOrder, summary: str, session_id: str) -> ArtifactRef:
    base_root = Path(os.getenv("DE_STATE_DIR", deps.root_path / ".de-state"))
    tenant_dir = base_root / (deps.config.tenant or "_default")
    artifact_dir = tenant_dir / "artifacts" / work_order.work_order_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    file_path = artifact_dir / f"{session_id}-summary.txt"
    file_path.write_text(summary, encoding="utf-8")
    timestamp = datetime.now(UTC).isoformat()
    return ArtifactRef(
        artifact_id=artifact_id(),
        kind="summary",
        name=f"{session_id}-summary.txt",
        uri=str(file_path),
        created_at=timestamp,
    )


def spawn_background_runner(deps: Deps, work_order_id: str, session_id: str, task_id: str) -> tuple[Path, int]:
    base_root = Path(os.getenv("DE_STATE_DIR", deps.root_path / ".de-state"))
    tenant_dir = base_root / (deps.config.tenant or "_default")
    log_dir = tenant_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{session_id}.log"

    env = os.environ.copy()
    src_path = str(deps.root_path / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else f"{src_path}{os.pathsep}{existing_pythonpath}"

    cmd = [
        sys.executable,
        "-m",
        "digital_employee.api.cli.main",
        "work-order",
        "_execute",
        work_order_id,
        "--session-id",
        session_id,
        "--task-id",
        task_id,
    ]
    with log_path.open("a", encoding="utf-8") as handle:
        process = subprocess.Popen(
            cmd,
            cwd=str(deps.root_path),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=handle,
            start_new_session=True,
        )
    process.returncode = 0
    return log_path, process.pid


def terminate_background_runner(record: SessionRecord) -> bool:
    runner_pid = record.session.metadata.get("runner_pid")
    if runner_pid in {None, ""}:
        return False
    try:
        os.killpg(int(runner_pid), signal.SIGTERM)
    except (ProcessLookupError, ValueError, PermissionError):
        return False
    return True
