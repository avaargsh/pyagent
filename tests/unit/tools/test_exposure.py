from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.tools.exposure import ToolExposurePlanner
from digital_employee.tools.registry import build_tool_registry


class ToolExposurePlannerTest(unittest.TestCase):
    def _profile(self) -> EmployeeProfile:
        return EmployeeProfile(
            employee_id="sales-assistant",
            display_name="Sales Assistant",
            default_provider="mock",
            approval_policy="high-risk-actions",
            skill_packs=["customer-followup"],
            allowed_tools=["knowledge-search", "send-email"],
            knowledge_scopes=["sales-playbook"],
        )

    def test_hides_high_risk_tool_when_prompt_is_non_actionable(self) -> None:
        planner = ToolExposurePlanner(max_tools_per_turn=4)
        registry = build_tool_registry(["knowledge-search", "send-email"])
        plan = planner.plan(profile=self._profile(), tools=registry.list_all(), prompt="Summarize the playbook")
        self.assertEqual([tool.name for tool in plan.exposed_tools], ["knowledge-search"])
        self.assertIn("send-email", plan.hidden_tools)

    def test_exposes_high_risk_tool_for_explicit_action_prompt(self) -> None:
        planner = ToolExposurePlanner(max_tools_per_turn=4)
        registry = build_tool_registry(["knowledge-search", "send-email"])
        plan = planner.plan(
            profile=self._profile(),
            tools=registry.list_all(),
            prompt="Send an email follow-up to the customer",
        )
        self.assertEqual([tool.name for tool in plan.exposed_tools], ["send-email", "knowledge-search"])


if __name__ == "__main__":
    unittest.main()
