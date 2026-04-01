from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.domain.errors import ToolPayloadError
from digital_employee.tools.schemas import ensure_valid_tool_payload, validate_tool_payload


class ToolSchemasTest(unittest.TestCase):
    def test_validate_tool_payload_reports_missing_required_fields(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        }
        issues = validate_tool_payload(schema, {})
        self.assertEqual(issues, ["missing required field: query"])

    def test_ensure_valid_tool_payload_raises_for_type_mismatch(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        }
        with self.assertRaises(ToolPayloadError):
            ensure_valid_tool_payload("knowledge-search", schema, {"query": 123})


if __name__ == "__main__":
    unittest.main()
