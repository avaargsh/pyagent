from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main


class CLIToolCommandsTest(unittest.TestCase):
    def test_tool_list_json(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--json", "tool", "list"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        names = [item["name"] for item in payload["data"]["tools"]]
        self.assertEqual(names, ["knowledge-search", "send-email"])

    def test_tool_show_json(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--json", "tool", "show", "send-email"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["data"]["tool"]["name"], "send-email")
        self.assertEqual(payload["data"]["tool"]["risk_level"], "high")
        self.assertTrue(payload["data"]["tool"]["requires_approval"])

    def test_tool_dry_run_allowed(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "--json",
                    "tool",
                    "dry-run",
                    "knowledge-search",
                    "--employee",
                    "sales-assistant",
                    "--input",
                    "{\"query\": \"pricing\", \"scope\": \"sales-playbook\"}",
                ]
            )
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["data"]["dry_run"]["policy_decision"], "allowed")
        self.assertTrue(payload["data"]["dry_run"]["executable"])

    def test_tool_dry_run_requires_approval(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "--json",
                    "tool",
                    "dry-run",
                    "send-email",
                    "--employee",
                    "sales-assistant",
                    "--input",
                    "{\"recipient\": \"x@example.com\", \"subject\": \"Hello\"}",
                ]
            )
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["data"]["dry_run"]["policy_decision"], "approval_required")
        self.assertFalse(payload["data"]["dry_run"]["executable"])

    def test_tool_dry_run_rejects_invalid_payload(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            code = main(
                [
                    "--json",
                    "tool",
                    "dry-run",
                    "knowledge-search",
                    "--employee",
                    "sales-assistant",
                    "--input",
                    "{\"scope\": \"sales-playbook\"}",
                ]
            )
        self.assertEqual(code, 2)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "tool_payload_invalid")


if __name__ == "__main__":
    unittest.main()
