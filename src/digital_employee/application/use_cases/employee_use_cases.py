"""Employee use cases."""

from __future__ import annotations

from dataclasses import asdict

from digital_employee.application.dto.common import CommandResult
from digital_employee.application.dto.employees import EmployeeTestView, EmployeeView
from digital_employee.application.services.deps import Deps
from digital_employee.domain.errors import NotFoundError


def list_employees(deps: Deps) -> CommandResult:
    employees = [
        EmployeeView(
            employee_id=profile.employee_id,
            display_name=profile.display_name,
            default_provider=profile.default_provider,
            approval_policy=profile.approval_policy,
        )
        for profile in deps.employee_registry.list_profiles()
    ]
    data = {"employees": [asdict(item) for item in employees]}
    human_lines = [f"{len(employees)} employees"]
    human_lines.extend(
        f"- {item.employee_id}: {item.display_name} [{item.default_provider}]"
        for item in employees
    )
    return CommandResult(command="employee list", data=data, human_lines=human_lines)


def show_employee(deps: Deps, employee_id: str) -> CommandResult:
    profile = deps.employee_registry.get_profile(employee_id)
    if profile is None:
        raise NotFoundError("employee", employee_id)

    data = {"employee": asdict(profile)}
    human_lines = [
        profile.display_name,
        f"ID: {profile.employee_id}",
        f"Provider: {profile.default_provider}",
        f"Skills: {', '.join(profile.skill_packs) or 'none'}",
        f"Allowed tools: {', '.join(profile.allowed_tools) or 'none'}",
        f"Knowledge scopes: {', '.join(profile.knowledge_scopes) or 'none'}",
        f"Approval policy: {profile.approval_policy}",
    ]
    return CommandResult(command="employee show", data=data, human_lines=human_lines)


async def test_employee(deps: Deps, employee_id: str, prompt: str) -> CommandResult:
    profile = deps.employee_registry.get_profile(employee_id)
    if profile is None:
        raise NotFoundError("employee", employee_id)
    runtime_cell = deps.runtime_manager.get_for_employee(profile.employee_id)

    completion = await runtime_cell.turn_engine.run(
        profile=profile,
        prompt=prompt,
    )
    view = EmployeeTestView(employee_id=employee_id, prompt=prompt, summary=completion.output_text)
    data = {"test": asdict(view)}
    human_lines = [
        f"Employee test for {profile.display_name}",
        f"Prompt: {prompt}",
        f"Summary: {completion.output_text}",
    ]
    return CommandResult(command="employee test", data=data, human_lines=human_lines)
