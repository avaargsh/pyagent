from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main


class CLIRootTest(unittest.TestCase):
    def test_version_command(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["version"])
        self.assertEqual(code, 0)
        self.assertIn("dectl version", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
