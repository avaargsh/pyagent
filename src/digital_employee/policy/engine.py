"""Policy evaluation for tool execution."""

from __future__ import annotations

from dataclasses import dataclass

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.policy.approvals import denies_exposure, requires_approval
from digital_employee.tools.models import ToolDefinition


@dataclass(slots=True)
class PolicyDecision:
    decision: str
    executable: bool
    requires_approval: bool
    reason: str


class PolicyEngine:
    def evaluate_tool_exposure(self, profile: EmployeeProfile, tool: ToolDefinition) -> PolicyDecision:
        if denies_exposure(profile, tool):
            return PolicyDecision(
                decision="denied",
                executable=False,
                requires_approval=False,
                reason=f"tool {tool.name} is not visible under policy {profile.approval_policy}",
            )
        if requires_approval(profile, tool):
            return PolicyDecision(
                decision="approval_required",
                executable=False,
                requires_approval=True,
                reason=f"policy {profile.approval_policy} requires approval",
            )
        return PolicyDecision(
            decision="allowed",
            executable=True,
            requires_approval=False,
            reason="tool can be exposed automatically",
        )

    def evaluate_tool_use(self, profile: EmployeeProfile, tool: ToolDefinition) -> PolicyDecision:
        exposure = self.evaluate_tool_exposure(profile, tool)
        if exposure.decision == "denied":
            return exposure
        if exposure.requires_approval:
            return PolicyDecision(
                decision="approval_required",
                executable=False,
                requires_approval=True,
                reason=exposure.reason,
            )
        return PolicyDecision(
            decision="allowed",
            executable=True,
            requires_approval=False,
            reason="tool can run automatically",
        )
