from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.work_order import CoordinatorPlan, WorkOrder


class WorkOrderTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        work_order = WorkOrder.create_new(
            employee_id="sales-assistant",
            input_text="Follow up on open quotes.",
            budget_tokens=1000,
            tenant="acme",
            config_snapshot_id="cfg_test_001",
            execution_mode="coordinated",
            coordinator_participants=["sales-assistant"],
            coordinator_plan=CoordinatorPlan(
                worker_employee_id="sales-assistant",
                selection_reason="tool-match:knowledge-search",
                required_tools=["knowledge-search"],
                matched_terms=["follow"],
            ),
        )
        restored = WorkOrder.from_dict(work_order.to_dict())
        self.assertEqual(restored.work_order_id, work_order.work_order_id)
        self.assertEqual(restored.employee_id, "sales-assistant")
        self.assertEqual(restored.status, "pending")
        self.assertEqual(restored.config_snapshot_id, "cfg_test_001")
        self.assertEqual(restored.execution_mode, "coordinated")
        self.assertEqual(restored.coordinator_participants, ["sales-assistant"])
        assert restored.coordinator_plan is not None
        self.assertEqual(restored.coordinator_plan.worker_employee_id, "sales-assistant")
        self.assertEqual(restored.coordinator_plan.required_tools, ["knowledge-search"])

    def test_single_mode_rejects_coordinator_fields(self) -> None:
        with self.assertRaises(ValueError):
            WorkOrder.create_new(
                employee_id="sales-assistant",
                input_text="Follow up on open quotes.",
                budget_tokens=1000,
                tenant="acme",
                execution_mode="single",
                coordinator_participants=["sales-assistant"],
            )

    def test_coordinator_plan_worker_must_be_participant(self) -> None:
        with self.assertRaises(ValueError):
            WorkOrder.create_new(
                employee_id="sales-assistant",
                input_text="Send a customer email.",
                budget_tokens=1000,
                tenant="acme",
                execution_mode="coordinated",
                coordinator_participants=["sales-assistant"],
                coordinator_plan=CoordinatorPlan(
                    worker_employee_id="outreach-specialist",
                    selection_reason="tool-match:send-email",
                ),
            )


if __name__ == "__main__":
    unittest.main()
