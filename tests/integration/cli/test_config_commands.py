from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main


class CLIConfigCommandsTest(unittest.TestCase):
    def test_config_show_json(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--json", "config", "show"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "config show")


if __name__ == "__main__":
    unittest.main()
