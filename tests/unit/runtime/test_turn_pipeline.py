from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.domain.session import ConversationSession
from digital_employee.memory.context_compactor import ContextCompactor
from digital_employee.policy.engine import PolicyEngine
from digital_employee.runtime.turn.context_assembler import ContextAssembler
from digital_employee.runtime.turn.engine import TurnEngine as PipelineTurnEngine
from digital_employee.runtime.turn_engine import TurnEngine as CompatTurnEngine
from digital_employee.tools.exposure import ToolExposurePlanner
from digital_employee.tools.registry import build_tool_registry


class TurnPipelineStructureTest(unittest.TestCase):
    def test_compat_turn_engine_reexports_pipeline_engine(self) -> None:
        self.assertIs(CompatTurnEngine, PipelineTurnEngine)

    def test_context_assembler_builds_metadata_and_exposure_plan(self) -> None:
        assembler = ContextAssembler(
            context_compactor=ContextCompactor(max_context_tokens=4, recent_message_window=1, compaction_target_tokens=6),
            tool_exposure_planner=ToolExposurePlanner(max_tools_per_turn=4),
            tool_registry=build_tool_registry(["knowledge-search", "send-email"]),
            policy_engine=PolicyEngine(),
        )
        profile = EmployeeProfile(
            employee_id="sales-assistant",
            display_name="Sales Assistant",
            default_provider="mock",
            approval_policy="manual",
            skill_packs=["customer-followup"],
            allowed_tools=["knowledge-search", "send-email"],
            knowledge_scopes=["sales-playbook"],
        )
        session = ConversationSession(session_id="ses_test", work_order_id="wo_test")
        session.add_message("user", "Summarize the sales playbook for follow-up planning")
        session.add_message("assistant", "Acknowledged")
        session.add_message("tool", "knowledge result one knowledge result two")

        packet = assembler.assemble(
            profile=profile,
            prompt="Summarize the sales playbook for follow-up planning",
            session=session,
            turn_index=1,
            budget_remaining=99,
            tool_observations=[],
            session_id=session.session_id,
        )

        self.assertEqual(packet.prepared_context.strategy, "autocompact")
        self.assertEqual(packet.request_metadata["employee_id"], "sales-assistant")
        self.assertEqual(packet.request_metadata["allowed_tools"], ["knowledge-search"])
        self.assertIn("send-email", packet.request_metadata["hidden_tools"])
        self.assertEqual(packet.request_metadata["context_compaction"]["strategy"], "autocompact")

    def test_policy_can_deny_tool_before_exposure(self) -> None:
        assembler = ContextAssembler(
            context_compactor=ContextCompactor(),
            tool_exposure_planner=ToolExposurePlanner(max_tools_per_turn=4),
            tool_registry=build_tool_registry(["knowledge-search", "send-email"]),
            policy_engine=PolicyEngine(),
        )
        profile = EmployeeProfile(
            employee_id="sales-assistant",
            display_name="Sales Assistant",
            default_provider="mock",
            approval_policy="read-only",
            skill_packs=["customer-followup"],
            allowed_tools=["knowledge-search", "send-email"],
            knowledge_scopes=["sales-playbook"],
        )
        session = ConversationSession(session_id="ses_test", work_order_id="wo_test")
        session.add_message("user", "Send a customer follow-up email")

        packet = assembler.assemble(
            profile=profile,
            prompt="Send a customer follow-up email",
            session=session,
            turn_index=1,
            budget_remaining=99,
            tool_observations=[],
            session_id=session.session_id,
        )

        self.assertEqual(packet.request_metadata["allowed_tools"], ["knowledge-search"])
        self.assertIn("send-email", packet.request_metadata["hidden_tools"])


if __name__ == "__main__":
    unittest.main()
