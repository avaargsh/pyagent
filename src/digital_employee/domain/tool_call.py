"""Tool call models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolCall:
    tool_name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolObservation:
    tool_name: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
