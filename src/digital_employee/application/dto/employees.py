"""Employee DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EmployeeView:
    employee_id: str
    display_name: str
    default_provider: str
    approval_policy: str


@dataclass(slots=True)
class EmployeeTestView:
    employee_id: str
    prompt: str
    summary: str
