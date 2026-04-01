"""Budget lifecycle for a single turn pipeline run."""

from __future__ import annotations

from digital_employee.runtime.budget import BudgetSnapshot, BudgetTracker


class BudgetController:
    def __init__(self, *, default_budget_tokens: int) -> None:
        self._default_budget_tokens = default_budget_tokens

    def start(self, budget_tokens: int | None = None) -> BudgetTracker:
        return BudgetTracker(budget_tokens or self._default_budget_tokens)

    def consume(self, tracker: BudgetTracker, tokens: int) -> BudgetSnapshot:
        return tracker.consume(tokens)

    def should_warn(self, snapshot: BudgetSnapshot) -> bool:
        return snapshot.remaining_tokens <= max(1, snapshot.total_tokens // 10)
