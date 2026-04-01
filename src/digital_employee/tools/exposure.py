"""Progressive tool disclosure for provider-facing context."""

from __future__ import annotations

import re
from dataclasses import dataclass

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.tools.models import ToolDefinition


@dataclass(slots=True)
class ToolExposurePlan:
    exposed_tools: list[ToolDefinition]
    hidden_tools: list[str]
    strategy: str


class ToolExposurePlanner:
    """Limit tool schemas to the subset relevant to the active turn."""

    _HIGH_RISK_ACTION_HINTS = {
        "send-email": {"email", "mail", "send", "notify", "reply"},
    }

    def __init__(self, *, max_tools_per_turn: int = 4, include_high_risk_by_default: bool = False) -> None:
        self._max_tools_per_turn = max_tools_per_turn
        self._include_high_risk_by_default = include_high_risk_by_default

    def plan(
        self,
        *,
        profile: EmployeeProfile,
        tools: list[ToolDefinition],
        prompt: str,
    ) -> ToolExposurePlan:
        normalized_prompt = self._tokenize(prompt)
        scored: list[tuple[int, int, ToolDefinition]] = []
        hidden: list[str] = []
        for tool in tools:
            score = self._score_tool(tool, normalized_prompt, profile)
            should_include = self._include_high_risk_by_default or tool.risk_level != "high"
            if tool.risk_level == "high" and not should_include:
                action_hints = self._HIGH_RISK_ACTION_HINTS.get(tool.name, set())
                should_include = bool(normalized_prompt & action_hints)
            if not should_include:
                hidden.append(tool.name)
                continue
            scored.append((score, 0 if tool.is_read_only else 1, tool))

        if not scored:
            fallback = [tool for tool in tools if tool.is_read_only or tool.risk_level == "low"]
            scored = [(0, 0 if tool.is_read_only else 1, tool) for tool in fallback]

        scored.sort(key=lambda item: (-item[0], item[1], item[2].name))
        exposed = [tool for _, _, tool in scored[: self._max_tools_per_turn]]
        hidden.extend(tool.name for _, _, tool in scored[self._max_tools_per_turn :])
        strategy = "progressive-disclosure" if hidden else "full-allow-list"
        return ToolExposurePlan(
            exposed_tools=exposed,
            hidden_tools=sorted(set(hidden)),
            strategy=strategy,
        )

    def _score_tool(
        self,
        tool: ToolDefinition,
        prompt_tokens: set[str],
        profile: EmployeeProfile,
    ) -> int:
        tool_tokens = (
            self._tokenize(tool.name)
            | self._tokenize(tool.description)
            | self._tokenize(tool.resource_kind)
            | self._tokenize(tool.side_effects)
        )
        tool_tokens.update(self._tokenize(" ".join(profile.knowledge_scopes)))
        score = len(prompt_tokens & tool_tokens)
        action_hints = self._HIGH_RISK_ACTION_HINTS.get(tool.name, set())
        if prompt_tokens & action_hints:
            score += 3
        if tool.is_read_only:
            score += 1
        return score

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9-]+", text.lower()) if token}
