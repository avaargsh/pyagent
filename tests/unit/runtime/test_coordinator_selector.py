from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.runtime.coordinator_selector import CoordinatorSelector


class CoordinatorSelectorTest(unittest.TestCase):
    def test_prefers_specialist_for_email_intent(self) -> None:
        selector = CoordinatorSelector()
        sales = EmployeeProfile(
            employee_id="sales-assistant",
            display_name="Sales Assistant",
            default_provider="mock",
            approval_policy="high-risk-actions",
            skill_packs=["customer-followup"],
            allowed_tools=["knowledge-search", "send-email"],
            knowledge_scopes=["sales-playbook"],
        )
        outreach = EmployeeProfile(
            employee_id="outreach-specialist",
            display_name="Outreach Specialist",
            default_provider="mock",
            approval_policy="high-risk-actions",
            skill_packs=["outbound-communication", "customer-reply"],
            allowed_tools=["send-email"],
            knowledge_scopes=["communication-playbook"],
        )

        selection = selector.select(
            participant_profiles=[sales, outreach],
            prompt="Please send email to jane@example.com with a short follow-up",
        )

        self.assertEqual(selection.worker_profile.employee_id, "outreach-specialist")
        self.assertIn("send-email", selection.required_tools)
        self.assertIn("tool-match:send-email", selection.reason)


if __name__ == "__main__":
    unittest.main()
