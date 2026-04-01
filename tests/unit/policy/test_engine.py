from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.policy.engine import PolicyEngine
from digital_employee.tools.registry import build_tool


class PolicyEngineTest(unittest.TestCase):
    def test_high_risk_tool_requires_approval(self) -> None:
        profile = EmployeeProfile(
            employee_id="sales-assistant",
            display_name="Sales Assistant",
            default_provider="mock",
            approval_policy="high-risk-actions",
            allowed_tools=["send-email"],
        )
        decision = PolicyEngine().evaluate_tool_use(profile, build_tool("send-email"))
        self.assertEqual(decision.decision, "approval_required")
        self.assertFalse(decision.executable)
        self.assertTrue(decision.requires_approval)

    def test_read_only_tool_is_allowed(self) -> None:
        profile = EmployeeProfile(
            employee_id="sales-assistant",
            display_name="Sales Assistant",
            default_provider="mock",
            approval_policy="high-risk-actions",
            allowed_tools=["knowledge-search"],
        )
        decision = PolicyEngine().evaluate_tool_use(profile, build_tool("knowledge-search"))
        self.assertEqual(decision.decision, "allowed")
        self.assertTrue(decision.executable)
        self.assertFalse(decision.requires_approval)

    def test_write_tool_can_be_denied_before_exposure(self) -> None:
        profile = EmployeeProfile(
            employee_id="sales-assistant",
            display_name="Sales Assistant",
            default_provider="mock",
            approval_policy="read-only",
            allowed_tools=["knowledge-search", "send-email"],
        )
        decision = PolicyEngine().evaluate_tool_exposure(profile, build_tool("send-email"))
        self.assertEqual(decision.decision, "denied")
        self.assertFalse(decision.executable)
        self.assertFalse(decision.requires_approval)


if __name__ == "__main__":
    unittest.main()
