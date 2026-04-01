"""Approval policy helpers."""

from __future__ import annotations

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.tools.models import ToolDefinition


def requires_approval(profile: EmployeeProfile, tool: ToolDefinition) -> bool:
    del profile
    return tool.requires_approval or tool.permission_mode == "approval_required"


def denies_exposure(profile: EmployeeProfile, tool: ToolDefinition) -> bool:
    if tool.name not in profile.allowed_tools:
        return True
    if profile.approval_policy == "read-only" and not tool.is_read_only:
        return True
    return False
