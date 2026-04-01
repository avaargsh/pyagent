from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.application.services.request_context import build_app_context


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class RuntimeManagerTest(unittest.TestCase):
    def test_get_for_employee_reuses_cached_cell(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)

        first = context.deps.runtime_manager.get_for_employee("sales-assistant")
        second = context.deps.runtime_manager.get_for_employee("sales-assistant")

        self.assertIs(first, second)
        self.assertEqual(first.key.employee_id, "sales-assistant")
        self.assertEqual(first.key.config_version, context.deps.config_version)

    def test_runtime_cells_are_partitioned_by_config_version(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)

        sales = context.deps.runtime_manager.get_for_employee("sales-assistant")
        alt = context.deps.runtime_manager.get_for_employee(
            "sales-assistant",
            config_version="cfg-alt-version",
        )

        self.assertEqual(sales.key.employee_id, alt.key.employee_id)
        self.assertNotEqual(sales.key.config_version, alt.key.config_version)
        self.assertIsNot(sales, alt)

    def test_runtime_cell_tool_registry_matches_employee_allow_list(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)

        cell = context.deps.runtime_manager.get_for_employee("sales-assistant")

        self.assertEqual(
            [tool.name for tool in cell.tool_registry.list_all()],
            sorted(context.deps.employee_registry.get_profile("sales-assistant").allowed_tools),
        )

    def test_invalidate_by_employee_rebuilds_cell(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)
        manager = context.deps.runtime_manager

        first = manager.get_for_employee("sales-assistant")
        manager.invalidate_by_employee("sales-assistant")
        second = manager.get_for_employee("sales-assistant")

        self.assertIsNot(first, second)


if __name__ == "__main__":
    unittest.main()
