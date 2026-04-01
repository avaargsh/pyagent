"""Explicit coordinator runtime for opt-in multi-employee execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from digital_employee.agents.registry import EmployeeRegistry
from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.domain.errors import NotFoundError
from digital_employee.domain.events import RunEvent
from digital_employee.domain.runtime_constraints import (
    COORDINATOR_STARTED_EVENT,
    COORDINATOR_WORKER_SELECTED_EVENT,
    ExecutionMode,
    normalize_participant_ids,
)
from digital_employee.domain.session import ConversationSession, generate_session_id
from digital_employee.domain.work_order import CoordinatorPlan, WorkOrder
from digital_employee.runtime.cell import RuntimeCell
from digital_employee.runtime.manager import RuntimeManager
from digital_employee.runtime.coordinator_selector import CoordinatorSelection, CoordinatorSelector
from digital_employee.runtime.turn_engine import TurnRunResult


@dataclass(slots=True)
class CoordinatorExecution:
    coordinator_profile: EmployeeProfile
    worker_profile: EmployeeProfile
    participant_ids: list[str]
    runtime_cell: RuntimeCell
    selection_reason: str
    required_tools: list[str]
    matched_terms: list[str]


class CoordinatorRuntime:
    def __init__(
        self,
        *,
        employee_registry: EmployeeRegistry,
        runtime_manager: RuntimeManager,
        selector: CoordinatorSelector | None = None,
    ) -> None:
        self._employee_registry = employee_registry
        self._runtime_manager = runtime_manager
        self._selector = selector or CoordinatorSelector()

    def resolve_execution(
        self,
        *,
        coordinator_employee_id: str,
        participant_ids: list[str] | None,
        config_version: str | None,
        prompt: str | None = None,
        coordinator_plan: CoordinatorPlan | None = None,
    ) -> CoordinatorExecution:
        coordinator_profile = self._require_profile(coordinator_employee_id)
        participant_profiles = self._load_participants(
            coordinator_employee_id=coordinator_employee_id,
            participant_ids=participant_ids,
        )
        selection = self._resolve_selection(
            participant_profiles=participant_profiles,
            prompt=prompt,
            coordinator_plan=coordinator_plan,
        )
        worker_profile = selection.worker_profile
        runtime_cell = self._runtime_manager.get_for_employee(
            worker_profile.employee_id,
            config_version=config_version,
        )
        return CoordinatorExecution(
            coordinator_profile=coordinator_profile,
            worker_profile=worker_profile,
            participant_ids=[profile.employee_id for profile in participant_profiles],
            runtime_cell=runtime_cell,
            selection_reason=selection.reason,
            required_tools=list(selection.required_tools),
            matched_terms=list(selection.matched_terms),
        )

    def select_plan(
        self,
        *,
        coordinator_employee_id: str,
        participant_ids: list[str] | None,
        prompt: str,
    ) -> CoordinatorPlan:
        execution = self.resolve_execution(
            coordinator_employee_id=coordinator_employee_id,
            participant_ids=participant_ids,
            config_version=None,
            prompt=prompt,
        )
        return CoordinatorPlan(
            worker_employee_id=execution.worker_profile.employee_id,
            selection_reason=execution.selection_reason,
            required_tools=list(execution.required_tools),
            matched_terms=list(execution.matched_terms),
        )

    async def run(
        self,
        *,
        work_order: WorkOrder,
        prompt: str,
        budget_tokens: int | None = None,
        session: ConversationSession | None = None,
        progress_callback: Callable[[ConversationSession, list[RunEvent]], None] | None = None,
    ) -> TurnRunResult:
        execution = self.resolve_execution(
            coordinator_employee_id=work_order.employee_id,
            participant_ids=work_order.coordinator_participants,
            config_version=work_order.config_snapshot_id,
            prompt=prompt,
            coordinator_plan=work_order.coordinator_plan,
        )
        session = session or ConversationSession(
            session_id=generate_session_id(),
            work_order_id=work_order.work_order_id,
        )
        coordination_metadata = {
            "execution_mode": ExecutionMode.COORDINATED.value,
            "coordinator_employee_id": execution.coordinator_profile.employee_id,
            "worker_employee_id": execution.worker_profile.employee_id,
            "participant_ids": list(execution.participant_ids),
            "selection_reason": execution.selection_reason,
            "required_tools": list(execution.required_tools),
        }
        session.metadata.update(coordination_metadata)
        initial_events = [
            RunEvent(
                event_type=COORDINATOR_STARTED_EVENT,
                work_order_id=work_order.work_order_id,
                payload={
                    "coordinator_employee_id": execution.coordinator_profile.employee_id,
                    "participant_ids": list(execution.participant_ids),
                },
            ),
            RunEvent(
                event_type=COORDINATOR_WORKER_SELECTED_EVENT,
                work_order_id=work_order.work_order_id,
                payload={
                    "worker_employee_id": execution.worker_profile.employee_id,
                    "coordinator_employee_id": execution.coordinator_profile.employee_id,
                    "selection_reason": execution.selection_reason,
                    "required_tools": list(execution.required_tools),
                    "matched_terms": list(execution.matched_terms),
                },
            ),
        ]

        def _publish_progress(updated_session: ConversationSession, updated_events: list[RunEvent]) -> None:
            updated_session.metadata.update(coordination_metadata)
            if progress_callback is not None:
                progress_callback(updated_session, [*initial_events, *updated_events])

        _publish_progress(session, [])
        result = await execution.runtime_cell.turn_engine.run(
            profile=execution.worker_profile,
            prompt=prompt,
            work_order_id=work_order.work_order_id,
            budget_tokens=budget_tokens,
            session=session,
            progress_callback=_publish_progress,
        )
        result.session.metadata.update(coordination_metadata)
        result.events = [*initial_events, *result.events]
        return result

    def _load_participants(
        self,
        *,
        coordinator_employee_id: str,
        participant_ids: list[str] | None,
    ) -> list[EmployeeProfile]:
        ordered: list[EmployeeProfile] = []
        seen: set[str] = set()
        for employee_id in normalize_participant_ids(participant_ids) or [coordinator_employee_id]:
            if employee_id not in seen:
                ordered.append(self._require_profile(employee_id))
                seen.add(employee_id)
        return ordered

    def _select_worker(
        self,
        *,
        participant_profiles: list[EmployeeProfile],
        prompt: str | None,
    ) -> CoordinatorSelection:
        if not prompt:
            return CoordinatorSelection(
                worker_profile=participant_profiles[0],
                reason="fallback:first-participant",
            )
        return self._selector.select(
            participant_profiles=participant_profiles,
            prompt=prompt,
        )

    def _resolve_selection(
        self,
        *,
        participant_profiles: list[EmployeeProfile],
        prompt: str | None,
        coordinator_plan: CoordinatorPlan | None,
    ) -> CoordinatorSelection:
        if coordinator_plan is None:
            return self._select_worker(
                participant_profiles=participant_profiles,
                prompt=prompt,
            )
        worker_profile = self._require_participant(
            participant_profiles=participant_profiles,
            employee_id=coordinator_plan.worker_employee_id,
        )
        return CoordinatorSelection(
            worker_profile=worker_profile,
            reason=coordinator_plan.selection_reason,
            required_tools=list(coordinator_plan.required_tools),
            matched_terms=list(coordinator_plan.matched_terms),
        )

    def _require_profile(self, employee_id: str) -> EmployeeProfile:
        profile = self._employee_registry.get_profile(employee_id)
        if profile is None:
            raise NotFoundError("employee", employee_id)
        return profile

    def _require_participant(
        self,
        *,
        participant_profiles: list[EmployeeProfile],
        employee_id: str,
    ) -> EmployeeProfile:
        for profile in participant_profiles:
            if profile.employee_id == employee_id:
                return profile
        raise NotFoundError("employee", employee_id)
