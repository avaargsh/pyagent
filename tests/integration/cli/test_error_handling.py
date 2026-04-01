"""Tests for CLI error handling — catch-all and config blocking."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main


class ExceptionCatchAllTest(unittest.TestCase):
    """Unexpected exceptions must be caught and converted to structured errors."""

    def test_unexpected_error_returns_exit_1_json(self) -> None:
        with patch(
            "digital_employee.api.cli.main.build_deps",
            side_effect=RuntimeError("boom"),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                code = main(["--json", "config", "show"])
            self.assertEqual(code, 10)
            payload = json.loads(stdout.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error"]["type"], "internal_error")
            self.assertEqual(payload["error"]["code"], 10)
            self.assertIsNone(payload["error"]["hint"])

    def test_unexpected_error_returns_exit_1_human(self) -> None:
        with patch(
            "digital_employee.api.cli.main.build_deps",
            side_effect=RuntimeError("boom"),
        ):
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                code = main(["config", "show"])
            self.assertEqual(code, 10)
            self.assertIn("unexpected error", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_input_file_error_maps_to_exit_2_json(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            code = main(
                [
                    "--json",
                    "employee",
                    "test",
                    "sales-assistant",
                    "--input-file",
                    "/tmp/does-not-exist.txt",
                ]
            )
        self.assertEqual(code, 2)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "input_file_unreadable")
        self.assertEqual(payload["error"]["code"], 2)

    def test_input_file_error_maps_to_exit_2_human(self) -> None:
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            code = main(
                [
                    "employee",
                    "test",
                    "sales-assistant",
                    "--input-file",
                    "/tmp/does-not-exist.txt",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("failed to read input file", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class ConfigBlockingTest(unittest.TestCase):
    """Commands other than config show/validate/version must fail on bad config."""

    def _run_with_bad_config(self, argv: list[str]) -> tuple[int, dict]:
        """Run CLI with a config dir that has no providers (triggers validation error)."""
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "configs"
            config_dir.mkdir()
            (config_dir / "system.yaml").write_text("runtime:\n  default_timeout_seconds: 30\n")
            (config_dir / "providers").mkdir()
            (config_dir / "agents").mkdir()
            (config_dir / "policies").mkdir()

            stdout = io.StringIO()
            with patch.dict(os.environ, {"DE_STATE_DIR": tmp}, clear=False):
                with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                    original_cwd = Path.cwd()
                    os.chdir(tmp)
                    try:
                        code = main(["--json"] + argv)
                    finally:
                        os.chdir(original_cwd)
            payload = json.loads(stdout.getvalue())
            return code, payload

    def test_work_order_create_blocked_on_bad_config(self) -> None:
        code, payload = self._run_with_bad_config(
            ["work-order", "create", "--employee", "x", "--input", "hi"]
        )
        self.assertEqual(code, 3)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "config_invalid")

    def test_employee_list_blocked_on_bad_config(self) -> None:
        code, payload = self._run_with_bad_config(["employee", "list"])
        self.assertEqual(code, 3)
        self.assertFalse(payload["ok"])

    def test_config_show_allowed_on_bad_config(self) -> None:
        code, payload = self._run_with_bad_config(["config", "show"])
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])

    def test_config_validate_allowed_on_bad_config(self) -> None:
        code, payload = self._run_with_bad_config(["config", "validate"])
        self.assertEqual(code, 3)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "config_invalid")

    def test_malformed_config_returns_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "configs"
            config_dir.mkdir()
            (config_dir / "system.yaml").write_text("runtime: [\n", encoding="utf-8")
            (config_dir / "providers").mkdir()
            (config_dir / "agents").mkdir()
            (config_dir / "policies").mkdir()

            stdout = io.StringIO()
            with patch.dict(os.environ, {"DE_STATE_DIR": tmp}, clear=False):
                with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                    original_cwd = Path.cwd()
                    os.chdir(tmp)
                    try:
                        code = main(["--json", "config", "show"])
                    finally:
                        os.chdir(original_cwd)

        self.assertEqual(code, 3)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["type"], "config_invalid")


if __name__ == "__main__":
    unittest.main()
