from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main
from tests.integration.cli.support import mark_background_session_stale


class CLIDoctorCommandsTest(unittest.TestCase):
    def test_doctor_reports_stale_background_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Prepare a customer follow-up plan",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id, "--background"])
                self.assertEqual(run_code, 0)
                session_id = json.loads(run_stdout.getvalue())["data"]["run"]["session_id"]

                with redirect_stdout(io.StringIO()):
                    tail_code = main(["--jsonl", "session", "tail", session_id, "--follow"])
                self.assertEqual(tail_code, 0)

                self.assertEqual(_wait_for_work_order_status(work_order_id), "completed")
                mark_background_session_stale(temp_dir, work_order_id, session_id)

                doctor_stdout = io.StringIO()
                with redirect_stdout(doctor_stdout):
                    doctor_code = main(["--json", "doctor"])
                self.assertEqual(doctor_code, 0)
                doctor_payload = json.loads(doctor_stdout.getvalue())
                self.assertEqual(doctor_payload["data"]["checks"][0]["status"], "warn")
                self.assertEqual(doctor_payload["data"]["summary"]["stale_background_sessions"], 1)
                stale = doctor_payload["data"]["stale_sessions"][0]
                self.assertEqual(stale["session_id"], session_id)
                self.assertEqual(stale["work_order_id"], work_order_id)
                self.assertEqual(stale["background"]["heartbeat_status"], "stale")
                self.assertEqual(stale["background"]["state"], "running")

                work_order_stdout = io.StringIO()
                with redirect_stdout(work_order_stdout):
                    work_order_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(work_order_code, 0)
                work_order_payload = json.loads(work_order_stdout.getvalue())
                self.assertEqual(work_order_payload["data"]["work_order"]["status"], "running")
                self.assertEqual(work_order_payload["data"]["background"]["heartbeat_status"], "stale")

                session_stdout = io.StringIO()
                with redirect_stdout(session_stdout):
                    session_code = main(["--json", "session", "get", session_id])
                self.assertEqual(session_code, 0)
                session_payload = json.loads(session_stdout.getvalue())
                self.assertEqual(session_payload["data"]["background"]["heartbeat_status"], "stale")


def _wait_for_work_order_status(work_order_id: str, *, attempts: int = 20, interval_seconds: float = 0.05) -> str | None:
    status = None
    for _ in range(attempts):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--json", "work-order", "get", work_order_id])
        if code == 0:
            payload = json.loads(stdout.getvalue())
            status = payload["data"]["work_order"]["status"]
            if status == "completed":
                return status
        time.sleep(interval_seconds)
    return status
if __name__ == "__main__":
    unittest.main()
