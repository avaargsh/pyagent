"""Typed dependency container (inspired by claude-code QueryDeps)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from digital_employee.agents.registry import EmployeeRegistry
from digital_employee.contracts.repositories import ApprovalRepository, SessionRepository, WorkOrderRepository
from digital_employee.infra.config.models import LoadedConfig
from digital_employee.memory.context_compactor import ContextCompactor
from digital_employee.observability.ledger import EventLedger
from digital_employee.observability.projections import ProjectionStore
from digital_employee.policy.engine import PolicyEngine
from digital_employee.providers.catalog import ProviderCatalog
from digital_employee.providers.factory import ProviderFactory
from digital_employee.providers.router import ProviderRouter
from digital_employee.runtime.hooks import HookDispatcher
from digital_employee.runtime.coordinator_runtime import CoordinatorRuntime
from digital_employee.runtime.manager import RuntimeManager
from digital_employee.runtime.task_supervisor import TaskSupervisor
from digital_employee.runtime.turn_engine import TurnEngine
from digital_employee.tools.exposure import ToolExposurePlanner
from digital_employee.tools.executor import ToolExecutor
from digital_employee.tools.registry import ToolRegistry


@dataclass(slots=True)
class Deps:
    """All dependencies required by use cases and CLI handlers."""

    config: LoadedConfig
    config_version: str
    validation_issues: list[str]
    root_path: Path
    work_order_repo: WorkOrderRepository
    session_repo: SessionRepository
    approval_repo: ApprovalRepository
    event_ledger: EventLedger
    projection_store: ProjectionStore
    employee_registry: EmployeeRegistry
    provider_catalog: ProviderCatalog
    provider_factory: ProviderFactory
    provider_router: ProviderRouter
    hook_dispatcher: HookDispatcher
    tool_registry: ToolRegistry
    tool_executor: ToolExecutor
    context_compactor: ContextCompactor
    tool_exposure_planner: ToolExposurePlanner
    policy_engine: PolicyEngine
    task_supervisor: TaskSupervisor
    turn_engine: TurnEngine
    runtime_manager: RuntimeManager
    coordinator_runtime: CoordinatorRuntime
