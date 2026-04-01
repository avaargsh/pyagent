from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.application.services.request_context import build_app_context
from digital_employee.domain.work_order import CoordinatorPlan, WorkOrder


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class CoordinatorRuntimeTest(unittest.TestCase):
    def test_run_adds_coordination_metadata_and_events(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)
        work_order = WorkOrder.create_new(
            employee_id="sales-assistant",
            input_text="Prepare a customer follow-up plan",
            budget_tokens=120,
            tenant=context.deps.config.tenant,
            config_snapshot_id=context.deps.config_version,
            execution_mode="coordinated",
            coordinator_participants=["sales-assistant"],
        )

        result = asyncio.run(
            context.deps.coordinator_runtime.run(
                work_order=work_order,
                prompt=work_order.input_text,
                budget_tokens=work_order.budget_tokens,
            )
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.session.metadata["execution_mode"], "coordinated")
        self.assertEqual(result.session.metadata["coordinator_employee_id"], "sales-assistant")
        self.assertEqual(result.session.metadata["worker_employee_id"], "sales-assistant")
        self.assertEqual(result.session.metadata["participant_ids"], ["sales-assistant"])
        self.assertEqual(
            [event.event_type for event in result.events[:2]],
            ["coordinator.started", "coordinator.worker_selected"],
        )

    def test_run_selects_specialist_when_prompt_matches_email_intent(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)
        work_order = WorkOrder.create_new(
            employee_id="sales-assistant",
            input_text="Please send email to jane@example.com with pricing details",
            budget_tokens=120,
            tenant=context.deps.config.tenant,
            config_snapshot_id=context.deps.config_version,
            execution_mode="coordinated",
            coordinator_participants=["sales-assistant", "outreach-specialist"],
        )

        result = asyncio.run(
            context.deps.coordinator_runtime.run(
                work_order=work_order,
                prompt=work_order.input_text,
                budget_tokens=work_order.budget_tokens,
            )
        )

        self.assertEqual(result.status, "waiting_approval")
        self.assertEqual(result.session.metadata["worker_employee_id"], "outreach-specialist")
        self.assertIn("send-email", result.session.metadata["required_tools"])
        self.assertIn(
            "selection_reason",
            result.session.metadata,
        )

    def test_run_uses_persisted_coordinator_plan_without_reselecting(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)
        work_order = WorkOrder.create_new(
            employee_id="sales-assistant",
            input_text="Please send email to jane@example.com with pricing details",
            budget_tokens=120,
            tenant=context.deps.config.tenant,
            config_snapshot_id=context.deps.config_version,
            execution_mode="coordinated",
            coordinator_participants=["sales-assistant", "outreach-specialist"],
            coordinator_plan=CoordinatorPlan(
                worker_employee_id="sales-assistant",
                selection_reason="persisted-selection",
                required_tools=["send-email"],
                matched_terms=["pricing"],
            ),
        )

        result = asyncio.run(
            context.deps.coordinator_runtime.run(
                work_order=work_order,
                prompt=work_order.input_text,
                budget_tokens=work_order.budget_tokens,
            )
        )

        self.assertEqual(result.session.metadata["worker_employee_id"], "sales-assistant")
        self.assertEqual(result.session.metadata["selection_reason"], "persisted-selection")
        self.assertEqual(
            result.events[1].payload["worker_employee_id"],
            "sales-assistant",
        )


if __name__ == "__main__":
    unittest.main()
