"""Tool use cases."""

from __future__ import annotations

from dataclasses import asdict

from digital_employee.application.dto.common import CommandResult
from digital_employee.application.dto.tools import ToolDetailView, ToolDryRunView, ToolView
from digital_employee.application.services.deps import Deps
from digital_employee.domain.errors import NotFoundError, ToolNotAllowedError
from digital_employee.tools.schemas import ensure_valid_tool_payload


def _applicable_employees(deps: Deps, tool_name: str) -> list[str]:
    employees = [
        profile.employee_id
        for profile in deps.employee_registry.list_profiles()
        if tool_name in profile.allowed_tools
    ]
    return sorted(employees)


def list_tools(deps: Deps) -> CommandResult:
    tools = [
        ToolView(
            name=tool.name,
            description=tool.description,
            risk_level=tool.risk_level,
            permission_mode=tool.permission_mode,
            applicable_employees=_applicable_employees(deps, tool.name),
        )
        for tool in deps.tool_registry.list_all()
    ]
    data = {"tools": [asdict(item) for item in tools]}
    human_lines = [f"{len(tools)} tools"]
    human_lines.extend(
        f"- {tool.name}: {tool.risk_level} / {tool.permission_mode} / employees={', '.join(tool.applicable_employees) or 'none'}"
        for tool in tools
    )
    return CommandResult(command="tool list", data=data, human_lines=human_lines)


def show_tool(deps: Deps, tool_name: str) -> CommandResult:
    tool = deps.tool_registry.require(tool_name)
    view = ToolDetailView(
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema,
        resource_kind=tool.resource_kind,
        risk_level=tool.risk_level,
        permission_mode=tool.permission_mode,
        side_effects=tool.side_effects,
        timeout_seconds=tool.timeout_seconds,
        requires_approval=tool.requires_approval,
        is_read_only=tool.is_read_only,
        is_concurrency_safe=tool.is_concurrency_safe,
        applicable_employees=_applicable_employees(deps, tool.name),
    )
    data = {"tool": asdict(view)}
    human_lines = [
        view.name,
        f"Risk: {view.risk_level}",
        f"Permission: {view.permission_mode}",
        f"Resource: {view.resource_kind}",
        f"Side effects: {view.side_effects}",
        f"Timeout: {view.timeout_seconds}s",
        f"Applicable employees: {', '.join(view.applicable_employees) or 'none'}",
    ]
    return CommandResult(command="tool show", data=data, human_lines=human_lines)


def dry_run_tool(deps: Deps, tool_name: str, employee_id: str, payload: dict) -> CommandResult:
    profile = deps.employee_registry.get_profile(employee_id)
    if profile is None:
        raise NotFoundError("employee", employee_id)

    tool = deps.tool_registry.require(tool_name)
    if tool.name not in profile.allowed_tools:
        raise ToolNotAllowedError(profile.employee_id, tool.name)

    ensure_valid_tool_payload(tool.name, tool.input_schema, payload)
    decision = deps.policy_engine.evaluate_tool_use(profile, tool)
    view = ToolDryRunView(
        tool_name=tool.name,
        employee_id=profile.employee_id,
        payload=payload,
        policy_decision=decision.decision,
        executable=decision.executable,
        approval_policy=profile.approval_policy,
        requires_approval=decision.requires_approval,
    )
    data = {"dry_run": asdict(view)}
    human_lines = [
        f"Tool dry-run for {tool.name}",
        f"Employee: {profile.employee_id}",
        f"Policy decision: {decision.decision}",
        f"Approval policy: {profile.approval_policy}",
        "Payload: valid",
    ]
    return CommandResult(command="tool dry-run", data=data, human_lines=human_lines)
