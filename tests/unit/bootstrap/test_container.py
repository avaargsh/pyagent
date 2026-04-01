from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.application.services.request_context import build_app_context, build_deps


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ControlPlaneContainerTest(unittest.TestCase):
    def test_build_app_context_exposes_facades_backed_by_shared_deps(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)

        self.assertIs(context.commands.deps, context.deps)
        self.assertIs(context.queries.deps, context.deps)
        self.assertEqual(context.validation_issues, [])
        self.assertEqual(context.deps.config_version, context.deps.runtime_manager.config_version)
        execution = context.deps.coordinator_runtime.resolve_execution(
            coordinator_employee_id="sales-assistant",
            participant_ids=None,
            config_version=context.deps.config_version,
        )
        self.assertIs(
            execution.runtime_cell,
            context.deps.runtime_manager.get_for_employee("sales-assistant"),
        )

        result = context.queries.list_employees()
        self.assertEqual(result.command, "employee list")
        self.assertIn("employees", result.data)

    def test_build_deps_remains_compatibility_wrapper(self) -> None:
        context = build_app_context(root_path=PROJECT_ROOT, output_json=True, no_input=True)
        deps = build_deps(root_path=PROJECT_ROOT, output_json=True, no_input=True)

        self.assertEqual(deps.config.profile, context.deps.config.profile)
        self.assertEqual(deps.config.tenant, context.deps.config.tenant)
        self.assertEqual(
            sorted(profile.employee_id for profile in deps.employee_registry.list_profiles()),
            sorted(profile.employee_id for profile in context.deps.employee_registry.list_profiles()),
        )


if __name__ == "__main__":
    unittest.main()
