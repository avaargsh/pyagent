"""Token budget accounting."""

from __future__ import annotations

from dataclasses import dataclass

from digital_employee.domain.errors import BudgetExceededError


@dataclass(slots=True)
class BudgetSnapshot:
    total_tokens: int
    used_tokens: int
    remaining_tokens: int


class BudgetTracker:
    def __init__(self, total_tokens: int) -> None:
        self._total_tokens = max(total_tokens, 1)
        self._used_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @property
    def used_tokens(self) -> int:
        return self._used_tokens

    @property
    def remaining_tokens(self) -> int:
        return self._total_tokens - self._used_tokens

    def consume(self, amount: int) -> BudgetSnapshot:
        normalized_amount = max(amount, 0)
        attempted = self._used_tokens + normalized_amount
        if attempted > self._total_tokens:
            raise BudgetExceededError(self._total_tokens, attempted)
        self._used_tokens = attempted
        return self.snapshot()

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            total_tokens=self._total_tokens,
            used_tokens=self._used_tokens,
            remaining_tokens=self.remaining_tokens,
        )
