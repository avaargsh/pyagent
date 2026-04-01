"""Task step model."""

from __future__ import annotations

from dataclasses import dataclass

from digital_employee.domain.enums import TaskStepStatus


@dataclass(slots=True)
class TaskStep:
    step_id: str
    title: str
    status: str = TaskStepStatus.PENDING.value
    input_summary: str = ""
    output_summary: str = ""
    retry_count: int = 0
