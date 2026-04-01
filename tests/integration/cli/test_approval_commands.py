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


class CLIApprovalCommandsTest(unittest.TestCase):
    def test_work_order_approval_resume_flow(self) -> None:
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
                            "Please send email to jane@example.com about renewal options",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                run_payload = json.loads(run_stdout.getvalue())
                self.assertEqual(run_payload["data"]["run"]["status"], "waiting_approval")
                approval_id = run_payload["data"]["approval"]["approval_id"]

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                get_payload = json.loads(get_stdout.getvalue())
                self.assertEqual(get_payload["data"]["work_order"]["status"], "waiting_approval")
                self.assertEqual(get_payload["data"]["work_order"]["last_approval_id"], approval_id)

                list_stdout = io.StringIO()
                with redirect_stdout(list_stdout):
                    list_code = main(["--json", "approval", "list"])
                self.assertEqual(list_code, 0)
                approvals = json.loads(list_stdout.getvalue())["data"]["approvals"]
                self.assertEqual(len(approvals), 1)
                self.assertEqual(approvals[0]["approval_id"], approval_id)

                pending_resume_stdout = io.StringIO()
                with redirect_stdout(pending_resume_stdout), redirect_stderr(io.StringIO()):
                    pending_resume_code = main(["--json", "work-order", "resume", work_order_id])
                self.assertEqual(pending_resume_code, 6)
                pending_resume_payload = json.loads(pending_resume_stdout.getvalue())
                self.assertEqual(pending_resume_payload["error"]["type"], "approval_required")

                decide_stdout = io.StringIO()
                with redirect_stdout(decide_stdout):
                    decide_code = main(
                        [
                            "--json",
                            "approval",
                            "decide",
                            approval_id,
                            "--decision",
                            "approve",
                            "--reason",
                            "manager approved the outbound message",
                        ]
                    )
                self.assertEqual(decide_code, 0)
                decide_payload = json.loads(decide_stdout.getvalue())
                self.assertEqual(decide_payload["data"]["approval"]["status"], "approved")

                resume_stdout = io.StringIO()
                with redirect_stdout(resume_stdout):
                    resume_code = main(["--json", "work-order", "resume", work_order_id])
                self.assertEqual(resume_code, 0)
                resume_payload = json.loads(resume_stdout.getvalue())
                self.assertEqual(resume_payload["data"]["run"]["status"], "completed")

                artifacts_stdout = io.StringIO()
                with redirect_stdout(artifacts_stdout):
                    artifacts_code = main(["--json", "work-order", "artifacts", work_order_id])
                self.assertEqual(artifacts_code, 0)
                artifacts = json.loads(artifacts_stdout.getvalue())["data"]["artifacts"]
                self.assertEqual(len(artifacts), 1)

    def test_approval_decide_requires_reason(self) -> None:
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
                            "Please send email to jane@example.com about pricing",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                approval_id = json.loads(run_stdout.getvalue())["data"]["approval"]["approval_id"]

                stderr = io.StringIO()
                stdout = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    decide_code = main(
                        [
                            "--json",
                            "approval",
                            "decide",
                            approval_id,
                            "--decision",
                            "approve",
                        ]
                    )
                self.assertEqual(decide_code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["error"]["type"], "approval_reason_required")

    def test_approval_decide_can_auto_resume_sync(self) -> None:
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
                            "Please send email to jane@example.com with the revised quote",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                approval_id = json.loads(run_stdout.getvalue())["data"]["approval"]["approval_id"]

                decide_stdout = io.StringIO()
                with redirect_stdout(decide_stdout):
                    decide_code = main(
                        [
                            "--json",
                            "approval",
                            "decide",
                            approval_id,
                            "--decision",
                            "approve",
                            "--reason",
                            "approved and resume immediately",
                            "--resume",
                        ]
                    )
                self.assertEqual(decide_code, 0)
                payload = json.loads(decide_stdout.getvalue())
                self.assertEqual(payload["data"]["approval"]["status"], "approved")
                self.assertEqual(payload["data"]["resume"]["run"]["status"], "completed")

    def test_approval_decide_can_auto_resume_background(self) -> None:
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
                            "Please send email to jane@example.com with the latest pricing update",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                run_payload = json.loads(run_stdout.getvalue())
                approval_id = run_payload["data"]["approval"]["approval_id"]
                session_id = run_payload["data"]["run"]["session_id"]

                decide_stdout = io.StringIO()
                with redirect_stdout(decide_stdout):
                    decide_code = main(
                        [
                            "--json",
                            "approval",
                            "decide",
                            approval_id,
                            "--decision",
                            "approve",
                            "--reason",
                            "approved and resume in background",
                            "--resume",
                            "--background",
                        ]
                    )
                self.assertEqual(decide_code, 0)
                payload = json.loads(decide_stdout.getvalue())
                self.assertEqual(payload["data"]["approval"]["status"], "approved")
                self.assertEqual(payload["data"]["resume"]["mode"], "background")
                self.assertEqual(payload["data"]["resume"]["run"]["session_id"], session_id)

                watch_stdout = io.StringIO()
                with redirect_stdout(watch_stdout):
                    watch_code = main(["--jsonl", "work-order", "watch", work_order_id, "--follow"])
                self.assertEqual(watch_code, 0)
                events = [json.loads(line) for line in watch_stdout.getvalue().splitlines() if line.strip()]
                self.assertIn("session.resumed", [item["event_type"] for item in events])

    def test_work_order_background_resume_flow(self) -> None:
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
                            "Please send email to jane@example.com about the updated proposal",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                run_payload = json.loads(run_stdout.getvalue())
                approval_id = run_payload["data"]["approval"]["approval_id"]
                session_id = run_payload["data"]["run"]["session_id"]

                with redirect_stdout(io.StringIO()):
                    decide_code = main(
                        [
                            "--json",
                            "approval",
                            "decide",
                            approval_id,
                            "--decision",
                            "approve",
                            "--reason",
                            "approved for async completion",
                        ]
                    )
                self.assertEqual(decide_code, 0)

                resume_stdout = io.StringIO()
                with redirect_stdout(resume_stdout):
                    resume_code = main(["--json", "work-order", "resume", work_order_id, "--background"])
                self.assertEqual(resume_code, 0)
                resume_payload = json.loads(resume_stdout.getvalue())
                self.assertEqual(resume_payload["data"]["mode"], "background")
                self.assertEqual(resume_payload["data"]["run"]["session_id"], session_id)

                watch_stdout = io.StringIO()
                with redirect_stdout(watch_stdout):
                    watch_code = main(["--jsonl", "work-order", "watch", work_order_id, "--follow"])
                self.assertEqual(watch_code, 0)
                events = [json.loads(line) for line in watch_stdout.getvalue().splitlines() if line.strip()]
                self.assertIn("session.resumed", [item["event_type"] for item in events])

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                get_payload = json.loads(get_stdout.getvalue())
                self.assertEqual(get_payload["data"]["work_order"]["status"], "completed")

    def test_approval_decide_background_requires_resume(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            code = main(
                [
                    "--json",
                    "approval",
                    "decide",
                    "ap_123",
                    "--decision",
                    "approve",
                    "--reason",
                    "noop",
                    "--background",
                ]
            )
        self.assertEqual(code, 2)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["error"]["type"], "background_requires_resume")


if __name__ == "__main__":
    unittest.main()
