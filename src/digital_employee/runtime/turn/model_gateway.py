"""Provider-facing completion gateway."""

from __future__ import annotations

from digital_employee.domain.employee_profile import EmployeeProfile
from digital_employee.domain.errors import DigitalEmployeeError, ProviderExecutionError
from digital_employee.providers.models import CompletionRequest, CompletionResult
from digital_employee.providers.router import ProviderRouter


class ModelGateway:
    def __init__(self, *, provider_router: ProviderRouter) -> None:
        self._provider_router = provider_router

    async def complete(
        self,
        *,
        profile: EmployeeProfile,
        prompt: str,
        metadata: dict,
        turn_index: int,
    ) -> tuple[str, CompletionResult]:
        provider = self._provider_router.resolve(profile.default_provider)
        request = CompletionRequest(
            system=f"Employee {profile.display_name}",
            prompt=prompt,
            metadata=dict(metadata),
            turn_index=turn_index,
        )
        try:
            result = await provider.complete(request)
        except DigitalEmployeeError:
            raise
        except Exception as error:
            raise ProviderExecutionError(provider.name, str(error)) from error
        return provider.name, result
