from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main


class CLISessionStreamingTest(unittest.TestCase):
    def test_background_run_and_session_tail_jsonl(self) -> None:
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
                            "Run a slow-run background planning task",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id, "--background"])
                self.assertEqual(run_code, 0)
                run_payload = json.loads(run_stdout.getvalue())
                session_id = run_payload["data"]["run"]["session_id"]

                tail_stdout = io.StringIO()
                with redirect_stdout(tail_stdout):
                    tail_code = main(["--jsonl", "session", "tail", session_id, "--follow"])
                self.assertEqual(tail_code, 0)
                lines = [line for line in tail_stdout.getvalue().splitlines() if line.strip()]
                self.assertGreaterEqual(len(lines), 1)
                payloads = [json.loads(line) for line in lines]
                self.assertEqual(payloads[0]["resource_id"], session_id)
                self.assertIn("event_type", payloads[0])
                self.assertIn("session.heartbeat", [item["event_type"] for item in payloads])

                session_stdout = io.StringIO()
                with redirect_stdout(session_stdout):
                    session_code = main(["--json", "session", "get", session_id])
                self.assertEqual(session_code, 0)
                session_payload = json.loads(session_stdout.getvalue())
                background = session_payload["data"]["background"]
                self.assertIsNotNone(background)
                self.assertEqual(background["state"], "completed")
                self.assertEqual(background["heartbeat_status"], "stopped")
                self.assertEqual(background["lease_timeout_seconds"], 900)
                self.assertTrue(background["runner_pid"])

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                get_payload = json.loads(get_stdout.getvalue())
                self.assertEqual(get_payload["data"]["work_order"]["status"], "completed")

    def test_jsonl_rejected_for_non_streaming_command(self) -> None:
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            code = main(["--jsonl", "tool", "list"])
        self.assertEqual(code, 2)
        self.assertIn("does not support --jsonl", stderr.getvalue())

    def test_background_run_and_work_order_watch_jsonl(self) -> None:
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
                            "Prepare a renewal summary for open opportunities",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                with redirect_stdout(io.StringIO()):
                    run_code = main(["--json", "work-order", "run", work_order_id, "--background"])
                self.assertEqual(run_code, 0)

                watch_stdout = io.StringIO()
                with redirect_stdout(watch_stdout):
                    watch_code = main(["--jsonl", "work-order", "watch", work_order_id, "--follow"])
                self.assertEqual(watch_code, 0)
                lines = [line for line in watch_stdout.getvalue().splitlines() if line.strip()]
                self.assertGreaterEqual(len(lines), 1)
                payloads = [json.loads(line) for line in lines]
                self.assertEqual(payloads[0]["resource_id"], work_order_id)
                self.assertIn("session_id", payloads[0]["payload"])

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                get_payload = json.loads(get_stdout.getvalue())
                self.assertEqual(get_payload["data"]["work_order"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
