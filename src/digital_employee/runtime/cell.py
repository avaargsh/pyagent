"""Runtime cell definitions."""

from __future__ import annotations

from dataclasses import dataclass

from digital_employee.memory.context_compactor import ContextCompactor
from digital_employee.policy.engine import PolicyEngine
from digital_employee.providers.catalog import ProviderCatalog
from digital_employee.providers.factory import ProviderFactory
from digital_employee.providers.router import ProviderRouter
from digital_employee.runtime.hooks import HookDispatcher
from digital_employee.runtime.task_supervisor import TaskSupervisor
from digital_employee.runtime.turn_engine import TurnEngine
from digital_employee.tools.exposure import ToolExposurePlanner
from digital_employee.tools.executor import ToolExecutor
from digital_employee.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class RuntimeCellKey:
    tenant: str | None
    employee_id: str
    config_version: str


@dataclass(slots=True)
class RuntimeCell:
    key: RuntimeCellKey
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
