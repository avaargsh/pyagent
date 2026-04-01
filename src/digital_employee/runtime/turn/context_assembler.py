"""Context preparation for each model turn."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.memory.context_compactor import ContextCompactor, PreparedContext
from digital_employee.policy.engine import PolicyEngine
from digital_employee.tools.exposure import ToolExposurePlan, ToolExposurePlanner
from digital_employee.tools.registry import ToolRegistry


@dataclass(slots=True)
class TurnContextPacket:
    prepared_context: PreparedContext
    exposure_plan: ToolExposurePlan
    request_metadata: dict[str, Any]


class ContextAssembler:
    def __init__(
        self,
        *,
        context_compactor: ContextCompactor,
        tool_exposure_planner: ToolExposurePlanner,
        tool_registry: ToolRegistry,
        policy_engine: PolicyEngine,
    ) -> None:
        self._context_compactor = context_compactor
        self._tool_exposure_planner = tool_exposure_planner
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine

    def assemble(
        self,
        *,
        profile: EmployeeProfile,
        prompt: str,
        session,
        turn_index: int,
        budget_remaining: int,
        tool_observations: list,
        session_id: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> TurnContextPacket:
        prepared_context = self._context_compactor.prepare(session)
        visible_tools = []
        policy_hidden: list[str] = []
        for tool in self._tool_registry.filter_by_names(profile.allowed_tools):
            decision = self._policy_engine.evaluate_tool_exposure(profile, tool)
            if decision.decision == "denied":
                policy_hidden.append(tool.name)
                continue
            visible_tools.append(tool)

        exposure_plan = self._tool_exposure_planner.plan(
            profile=profile,
            tools=visible_tools,
            prompt=prompt,
        )
        exposure_plan.hidden_tools = sorted(set(exposure_plan.hidden_tools + policy_hidden))
        request_metadata = {
            "employee_id": profile.employee_id,
            "allowed_tools": [tool.name for tool in exposure_plan.exposed_tools],
            "skill_packs": list(profile.skill_packs),
            "knowledge_scopes": list(profile.knowledge_scopes),
            "approval_policy": profile.approval_policy,
            "budget_remaining": budget_remaining,
            "tool_observations": [asdict(item) for item in tool_observations],
            "turn_index": turn_index,
            "session_id": session_id,
            "exposed_tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "risk_level": tool.risk_level,
                    "permission_mode": tool.permission_mode,
                }
                for tool in exposure_plan.exposed_tools
            ],
            "hidden_tools": list(exposure_plan.hidden_tools),
            "context_compaction": {
                "strategy": prepared_context.strategy,
                "summary": prepared_context.summary,
                "total_tokens": prepared_context.total_tokens,
                "retained_tokens": prepared_context.retained_tokens,
            },
            "recent_context": [
                {
                    "role": message.role,
                    "content": message.content,
                    "metadata": dict(message.metadata),
                }
                for message in prepared_context.recent_messages
            ],
        }
        if extra_metadata:
            request_metadata.update(extra_metadata)
        return TurnContextPacket(
            prepared_context=prepared_context,
            exposure_plan=exposure_plan,
            request_metadata=request_metadata,
        )
