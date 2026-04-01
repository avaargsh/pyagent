"""Employee profile model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EmployeeProfile:
    employee_id: str
    display_name: str
    default_provider: str
    approval_policy: str
    skill_packs: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    knowledge_scopes: list[str] = field(default_factory=list)
