"""Employee registry assembly."""

from __future__ import annotations

from digital_employee.agents.loader import load_employee_profiles
from digital_employee.agents.registry import EmployeeRegistry


def assemble_employee_registry(config) -> EmployeeRegistry:
    return EmployeeRegistry(load_employee_profiles(config))
