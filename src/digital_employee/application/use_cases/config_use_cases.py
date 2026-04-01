"""Configuration use cases."""

from __future__ import annotations

from dataclasses import asdict

from digital_employee.application.dto.common import CommandResult
from digital_employee.application.services.deps import Deps
from digital_employee.domain.errors import ConfigError


def show_config(deps: Deps) -> CommandResult:
    config = deps.config
    data = {
        "profile": config.profile,
        "tenant": config.tenant,
        "system": asdict(config.system),
        "providers": {name: asdict(provider) for name, provider in config.providers.items()},
        "employees": {name: asdict(employee) for name, employee in config.employees.items()},
        "policies": config.policies,
    }
    human_lines = [
        "Effective configuration",
        f"Profile: {config.profile or 'default'}",
        f"Tenant: {config.tenant or 'none'}",
        f"Base URL: {config.system.api.base_url}",
        f"Providers: {', '.join(sorted(config.providers))}",
        f"Employees: {', '.join(sorted(config.employees))}",
    ]
    return CommandResult(command="config show", data=data, human_lines=human_lines)


def validate_config(deps: Deps) -> CommandResult:
    issues = deps.validation_issues
    if issues:
        summary = "; ".join(issues)
        raise ConfigError(
            message=f"configuration is invalid: {summary}",
            hint="fix the reported issues and rerun 'dectl config validate'",
        )

    return CommandResult(
        command="config validate",
        data={"valid": True, "issues": []},
        human_lines=["Config is valid"],
    )
