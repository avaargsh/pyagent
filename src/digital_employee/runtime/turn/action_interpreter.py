"""Completion and tool-call normalization helpers."""

from __future__ import annotations

from typing import Any

from digital_employee.domain.tool_call import ToolCall, ToolObservation
from digital_employee.providers.models import CompletionResult


class ActionInterpreter:
    def normalize_tool_call(self, payload: dict[str, Any]) -> ToolCall:
        tool_name = str(payload.get("tool_name") or payload.get("name") or "")
        tool_payload = dict(payload.get("payload") or payload.get("input") or {})
        return ToolCall(tool_name=tool_name, payload=tool_payload)

    def build_follow_up_prompt(
        self,
        original_prompt: str,
        completion_text: str,
        tool_observations: list[ToolObservation],
    ) -> str:
        lines = [
            original_prompt,
            "",
            f"Previous completion: {completion_text}",
            "Tool observations:",
        ]
        lines.extend(
            f"- {item.tool_name} [{item.status}]: {item.payload}"
            for item in tool_observations
        )
        return "\n".join(lines)

    def usage_tokens(self, result: CompletionResult) -> int:
        usage_total = sum(value for value in result.usage.values() if isinstance(value, int) and value > 0)
        if usage_total > 0:
            return usage_total
        fallback = len(result.text.split())
        return max(fallback, 1)
