"""Provider contracts."""

from __future__ import annotations

from typing import Protocol

from digital_employee.providers.models import CompletionRequest, CompletionResult


class Provider(Protocol):
    name: str

    async def complete(self, request: CompletionRequest) -> CompletionResult: ...
