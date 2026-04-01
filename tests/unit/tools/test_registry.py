from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.errors import ToolNotFoundError
from digital_employee.tools.registry import build_tool, build_tool_registry


class ToolRegistryTest(unittest.TestCase):
    def test_build_tool_registry_registers_known_tools(self) -> None:
        registry = build_tool_registry(["send-email", "knowledge-search", "send-email"])
        tools = registry.list_all()
        self.assertEqual([tool.name for tool in tools], ["knowledge-search", "send-email"])

    def test_knowledge_search_handler_returns_observation(self) -> None:
        definition = build_tool("knowledge-search")
        observation = asyncio.run(definition.handler({"query": "pricing", "scope": "sales"}))
        self.assertEqual(observation.tool_name, "knowledge-search")
        self.assertEqual(observation.status, "ok")
        self.assertEqual(observation.payload["scope"], "sales")

    def test_unknown_tool_raises(self) -> None:
        with self.assertRaises(ToolNotFoundError):
            build_tool("missing-tool")


if __name__ == "__main__":
    unittest.main()
