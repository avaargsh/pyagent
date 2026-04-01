"""Shared runtime constraint constants and normalization helpers."""

from __future__ import annotations

from enum import StrEnum

from digital_employee.domain.enums import WorkOrderStatus


class ExecutionMode(StrEnum):
    SINGLE = "single"
    COORDINATED = "coordinated"


class DispatchMode(StrEnum):
    FOREGROUND = "foreground"
    BACKGROUND = "background"


class BackgroundState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = WorkOrderStatus.WAITING_APPROVAL.value
    COMPLETED = WorkOrderStatus.COMPLETED.value
    FAILED = WorkOrderStatus.FAILED.value
    CANCELLED = WorkOrderStatus.CANCELLED.value


COORDINATOR_STARTED_EVENT = "coordinator.started"
COORDINATOR_WORKER_SELECTED_EVENT = "coordinator.worker_selected"

BACKGROUND_METADATA_KEYS = (
    "dispatch_mode",
    "task_id",
    "runner_pid",
    "log_path",
    "lease_timeout_seconds",
    "background_state",
    "background_started_at",
    "background_last_heartbeat_at",
    "background_finished_at",
)

COORDINATION_METADATA_KEYS = (
    "execution_mode",
    "dispatch_mode",
    "coordinator_employee_id",
    "worker_employee_id",
    "participant_ids",
    "selection_reason",
    "required_tools",
    "matched_terms",
)

BACKGROUND_TERMINAL_STATES = frozenset(
    {
        BackgroundState.COMPLETED.value,
        BackgroundState.FAILED.value,
        BackgroundState.WAITING_APPROVAL.value,
        BackgroundState.CANCELLED.value,
    }
)


def normalize_execution_mode(value: str | ExecutionMode | None) -> ExecutionMode:
    if isinstance(value, ExecutionMode):
        return value
    candidate = str(value or ExecutionMode.SINGLE.value).strip().lower()
    try:
        return ExecutionMode(candidate)
    except ValueError as error:
        raise ValueError(f"unsupported execution_mode: {value}") from error


def normalize_dispatch_mode(value: str | DispatchMode | None) -> DispatchMode | None:
    if value in {None, ""}:
        return None
    if isinstance(value, DispatchMode):
        return value
    candidate = str(value).strip().lower()
    try:
        return DispatchMode(candidate)
    except ValueError as error:
        raise ValueError(f"unsupported dispatch_mode: {value}") from error


def normalize_background_state(value: str | BackgroundState | None) -> BackgroundState | None:
    if value in {None, ""}:
        return None
    if isinstance(value, BackgroundState):
        return value
    candidate = str(value).strip().lower()
    try:
        return BackgroundState(candidate)
    except ValueError as error:
        raise ValueError(f"unsupported background_state: {value}") from error


def is_terminal_background_state(value: str | BackgroundState | None) -> bool:
    try:
        state = normalize_background_state(value)
    except ValueError:
        return False
    return bool(state and state.value in BACKGROUND_TERMINAL_STATES)


def normalize_string_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        candidate = str(raw).strip()
        if not candidate or candidate in seen:
            continue
        ordered.append(candidate)
        seen.add(candidate)
    return ordered


def normalize_participant_ids(values: list[str] | tuple[str, ...] | None) -> list[str]:
    return normalize_string_list(values)
