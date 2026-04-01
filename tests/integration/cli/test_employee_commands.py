from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main


class CLIEmployeeCommandsTest(unittest.TestCase):
    def test_employee_list_json(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--json", "employee", "list"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        employee_ids = [item["employee_id"] for item in payload["data"]["employees"]]
        self.assertEqual(employee_ids, ["outreach-specialist", "sales-assistant"])

    def test_employee_test_json(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "--json",
                    "employee",
                    "test",
                    "sales-assistant",
                    "--input",
                    "Generate a follow-up draft",
                ]
            )
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("Mock plan", payload["data"]["test"]["summary"])


if __name__ == "__main__":
    unittest.main()
