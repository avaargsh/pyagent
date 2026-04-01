from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.agents.assembler import assemble_employee_registry
from digital_employee.infra.config.loader import load_app_config


ROOT = Path(__file__).resolve().parents[3]


class EmployeeAssemblerTest(unittest.TestCase):
    def test_registry_contains_sales_assistant(self) -> None:
        config = load_app_config(ROOT)
        registry = assemble_employee_registry(config)
        profile = registry.get_profile("sales-assistant")
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertIn("send-email", profile.allowed_tools)

    def test_registry_contains_outreach_specialist(self) -> None:
        config = load_app_config(ROOT)
        registry = assemble_employee_registry(config)
        profile = registry.get_profile("outreach-specialist")
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.allowed_tools, ["send-email"])


if __name__ == "__main__":
    unittest.main()
