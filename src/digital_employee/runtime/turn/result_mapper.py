"""Mapping raw run state into stable turn results."""

from __future__ import annotations

from dataclasses import dataclass, field

from digital_employee.domain.session import ConversationSession
from digital_employee.domain.tool_call import ToolObservation
from digital_employee.domain.events import RunEvent


@dataclass(slots=True)
class TurnRunResult:
    output_text: str
    provider_name: str
    status: str
    turns: int
    budget_used: int
    budget_remaining: int
    session_id: str
    compaction_strategy: str
    session: ConversationSession
    approval_id: str | None = None
    exposed_tools: list[str] = field(default_factory=list)
    tool_observations: list[ToolObservation] = field(default_factory=list)
    events: list[RunEvent] = field(default_factory=list)


class ResultMapper:
    def completed(
        self,
        *,
        output_text: str,
        provider_name: str,
        turns: int,
        budget_used: int,
        budget_remaining: int,
        session,
        compaction_strategy: str,
        exposed_tools: list[str],
        tool_observations: list[ToolObservation],
        events: list[RunEvent],
    ) -> TurnRunResult:
        return TurnRunResult(
            output_text=output_text,
            provider_name=provider_name,
            status="completed",
            turns=turns,
            budget_used=budget_used,
            budget_remaining=budget_remaining,
            session_id=session.session_id,
            compaction_strategy=compaction_strategy,
            session=session,
            exposed_tools=exposed_tools,
            tool_observations=tool_observations,
            events=events,
        )

    def waiting_approval(
        self,
        *,
        output_text: str,
        provider_name: str,
        turns: int,
        budget_used: int,
        budget_remaining: int,
        session,
        compaction_strategy: str,
        approval_id: str,
        exposed_tools: list[str],
        tool_observations: list[ToolObservation],
        events: list[RunEvent],
    ) -> TurnRunResult:
        return TurnRunResult(
            output_text=output_text,
            provider_name=provider_name,
            status="waiting_approval",
            turns=turns,
            budget_used=budget_used,
            budget_remaining=budget_remaining,
            session_id=session.session_id,
            compaction_strategy=compaction_strategy,
            session=session,
            approval_id=approval_id,
            exposed_tools=exposed_tools,
            tool_observations=tool_observations,
            events=events,
        )
