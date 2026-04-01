"""Provider models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CompletionRequest:
    system: str
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)
    turn_index: int = 1


@dataclass(slots=True)
class CompletionResult:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    stop_reason: str = "completed"
