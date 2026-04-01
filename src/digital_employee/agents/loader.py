"""Employee profile loading."""

from __future__ import annotations

from digital_employee.domain.employee_profile import EmployeeProfile


def load_employee_profiles(config) -> list[EmployeeProfile]:
    profiles: list[EmployeeProfile] = []
    for employee_config in config.employees.values():
        profiles.append(
            EmployeeProfile(
                employee_id=employee_config.id,
                display_name=employee_config.display_name,
                default_provider=employee_config.default_provider,
                approval_policy=employee_config.approval_policy,
                skill_packs=list(employee_config.skill_packs),
                allowed_tools=list(employee_config.allowed_tools),
                knowledge_scopes=list(employee_config.knowledge_scopes),
            )
        )
    return profiles
