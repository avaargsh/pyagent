from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from digital_employee.domain.events import RunEvent
from digital_employee.domain.session import ConversationSession, SessionRecord
from digital_employee.infra.repositories.sessions import FileSessionRepository


class FileSessionRepositoryTest(unittest.TestCase):
    def test_save_and_get_session_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = FileSessionRepository(root, tenant="tenant-a")
            session = ConversationSession(session_id="sess_1", work_order_id="wo_1", employee_id="emp1")
            session.close(current_stage="completed", turns=1, budget_used=5, budget_remaining=10)
            record = SessionRecord(
                session=session,
                events=[RunEvent(event_type="turn.completed", work_order_id="wo_1")],
            )

            repo.save(record)
            fetched = repo.get("sess_1")
            self.assertIsNotNone(fetched)
            assert fetched is not None
            self.assertEqual(fetched.session.session_id, "sess_1")
            self.assertEqual(len(fetched.events), 1)


if __name__ == "__main__":
    unittest.main()
