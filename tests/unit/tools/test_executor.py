from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.errors import ToolPayloadError
from digital_employee.tools.executor import ToolExecutor
from digital_employee.tools.registry import build_tool


class ToolExecutorTest(unittest.TestCase):
    def test_execute_runs_tool_handler(self) -> None:
        executor = ToolExecutor()
        observation = asyncio.run(
            executor.execute(
                build_tool("knowledge-search"),
                {"query": "pricing", "scope": "sales"},
            )
        )
        self.assertEqual(observation.tool_name, "knowledge-search")
        self.assertEqual(observation.status, "ok")

    def test_execute_validates_payload(self) -> None:
        executor = ToolExecutor()
        with self.assertRaises(ToolPayloadError):
            asyncio.run(executor.execute(build_tool("send-email"), {"subject": "Missing recipient"}))


if __name__ == "__main__":
    unittest.main()
