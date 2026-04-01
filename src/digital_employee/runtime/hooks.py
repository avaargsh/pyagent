"""Lifecycle hook system."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable


class HookPoint(StrEnum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_COMPLETION = "pre_completion"
    POST_COMPLETION = "post_completion"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    BUDGET_WARNING = "budget_warning"


@dataclass(slots=True)
class HookContext:
    hook_point: HookPoint
    work_order_id: str | None
    payload: dict[str, Any]
    blocked: bool = False
    modified_payload: dict[str, Any] | None = None


HookHandler = Callable[[HookContext], None]


class HookDispatcher:
    """Dispatches lifecycle hooks to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[HookPoint, list[HookHandler]] = defaultdict(list)

    def on(self, point: HookPoint, handler: HookHandler) -> None:
        self._handlers[point].append(handler)

    def fire(self, context: HookContext) -> HookContext:
        for handler in self._handlers.get(context.hook_point, []):
            handler(context)
            if context.blocked:
                break
        return context


class NullHookDispatcher(HookDispatcher):
    """No-op dispatcher used before the hook system is wired."""

    def fire(self, context: HookContext) -> HookContext:
        return context
