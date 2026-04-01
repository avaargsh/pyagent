from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main


class CLISessionCommandsTest(unittest.TestCase):
    def test_session_commands_after_work_order_run(self) -> None:
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
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                run_payload = json.loads(run_stdout.getvalue())
                session_id = run_payload["data"]["run"]["session_id"]

                list_stdout = io.StringIO()
                with redirect_stdout(list_stdout):
                    list_code = main(["--json", "session", "list", "--work-order", work_order_id])
                self.assertEqual(list_code, 0)
                list_payload = json.loads(list_stdout.getvalue())
                self.assertEqual(list_payload["data"]["sessions"][0]["session_id"], session_id)

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "session", "get", session_id])
                self.assertEqual(get_code, 0)
                get_payload = json.loads(get_stdout.getvalue())
                self.assertEqual(get_payload["data"]["session"]["session_id"], session_id)

                tail_stdout = io.StringIO()
                with redirect_stdout(tail_stdout):
                    tail_code = main(["--json", "session", "tail", session_id])
                self.assertEqual(tail_code, 0)
                tail_payload = json.loads(tail_stdout.getvalue())
                self.assertGreaterEqual(len(tail_payload["data"]["events"]), 1)

                export_stdout = io.StringIO()
                with redirect_stdout(export_stdout):
                    export_code = main(["--json", "session", "export", session_id])
                self.assertEqual(export_code, 0)
                export_payload = json.loads(export_stdout.getvalue())
                self.assertEqual(export_payload["data"]["export"]["session"]["session_id"], session_id)


if __name__ == "__main__":
    unittest.main()
