from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.events import RunEvent
from digital_employee.domain.session import ConversationSession
from digital_employee.infra.repositories.events import FileEventLedgerRepository
from digital_employee.infra.repositories.projections import FileSessionProjectionRepository
from digital_employee.observability.ledger import EventLedger
from digital_employee.observability.projections import ProjectionStore


class EventLedgerTest(unittest.TestCase):
    def test_sync_session_events_deduplicates_repeated_record_saves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = EventLedger(FileEventLedgerRepository(root, tenant="acme"), tenant="acme")
            event = RunEvent(
                event_type="turn.started",
                work_order_id="wo_test",
                payload={"step": "start"},
            )

            first = ledger.sync_session_events(session_id="ses_test", events=[event])
            second = ledger.sync_session_events(session_id="ses_test", events=[event])

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)
            self.assertEqual(second[0].session_id, "ses_test")
            self.assertEqual(second[0].tenant, "acme")

    def test_projection_store_can_rebuild_session_record_from_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = EventLedger(FileEventLedgerRepository(root, tenant="acme"), tenant="acme")
            store = ProjectionStore(FileSessionProjectionRepository(root, tenant="acme"))
            session = ConversationSession(
                session_id="ses_test",
                work_order_id="wo_test",
                employee_id="sales-assistant",
            )
            session.metadata.update(
                {
                    "execution_mode": "coordinated",
                    "dispatch_mode": "foreground",
                    "coordinator_employee_id": "sales-assistant",
                    "worker_employee_id": "outreach-specialist",
                    "participant_ids": ["sales-assistant", "outreach-specialist"],
                    "selection_reason": "tool-match:send-email",
                    "required_tools": ["send-email"],
                    "matched_terms": ["pricing"],
                }
            )
            session.add_message("user", "Hello")
            event = RunEvent(event_type="coordinator.worker_selected", work_order_id="wo_test")

            ledger_events = ledger.sync_session_events(session_id=session.session_id, events=[event])
            projection = store.sync_session(session, ledger_events)
            rebuilt = store.as_session_record(projection, ledger_events)

            self.assertEqual(rebuilt.session.session_id, session.session_id)
            self.assertEqual(len(rebuilt.events), 1)
            self.assertEqual(rebuilt.events[0].event_type, "coordinator.worker_selected")
            self.assertEqual(projection.coordination["worker_employee_id"], "outreach-specialist")
            self.assertEqual(projection.coordination["required_tools"], ["send-email"])

    def test_projection_store_can_derive_coordination_from_ledger_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = EventLedger(FileEventLedgerRepository(root, tenant="acme"), tenant="acme")
            store = ProjectionStore(FileSessionProjectionRepository(root, tenant="acme"))
            session = ConversationSession(
                session_id="ses_coord",
                work_order_id="wo_coord",
                employee_id="sales-assistant",
            )
            session.add_message("user", "Please send email to jane@example.com")
            events = [
                RunEvent(
                    event_type="coordinator.started",
                    work_order_id="wo_coord",
                    payload={
                        "coordinator_employee_id": "sales-assistant",
                        "participant_ids": ["sales-assistant", "outreach-specialist"],
                    },
                ),
                RunEvent(
                    event_type="coordinator.worker_selected",
                    work_order_id="wo_coord",
                    payload={
                        "coordinator_employee_id": "sales-assistant",
                        "worker_employee_id": "outreach-specialist",
                        "selection_reason": "tool-match:send-email",
                        "required_tools": ["send-email"],
                        "matched_terms": ["email"],
                    },
                ),
            ]

            ledger_events = ledger.sync_session_events(session_id=session.session_id, events=events)
            projection = store.sync_session(session, ledger_events)

            self.assertEqual(projection.coordination["execution_mode"], "coordinated")
            self.assertEqual(projection.coordination["worker_employee_id"], "outreach-specialist")
            self.assertEqual(projection.coordination["participant_ids"], ["sales-assistant", "outreach-specialist"])


if __name__ == "__main__":
    unittest.main()
