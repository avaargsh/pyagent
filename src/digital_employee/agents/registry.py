"""Employee registry."""

from __future__ import annotations

from digital_employee.domain.employee_profile import EmployeeProfile


class EmployeeRegistry:
    def __init__(self, profiles: list[EmployeeProfile]) -> None:
        self._profiles = {profile.employee_id: profile for profile in profiles}

    def get_profile(self, employee_id: str) -> EmployeeProfile | None:
        return self._profiles.get(employee_id)

    def list_profiles(self) -> list[EmployeeProfile]:
        return [self._profiles[key] for key in sorted(self._profiles)]
