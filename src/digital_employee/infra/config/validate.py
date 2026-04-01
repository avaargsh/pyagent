"""Configuration validation."""

from __future__ import annotations

from digital_employee.tools.registry import is_known_tool


def validate_loaded_config(config) -> list[str]:
    issues: list[str] = []
    if not config.providers:
        issues.append("at least one provider must be configured")
    if not config.employees:
        issues.append("at least one employee must be configured")
    if config.system.runtime.max_context_tokens <= 0:
        issues.append("runtime max_context_tokens must be positive")
    if config.system.runtime.recent_message_window <= 0:
        issues.append("runtime recent_message_window must be positive")
    if config.system.runtime.compaction_target_tokens <= 0:
        issues.append("runtime compaction_target_tokens must be positive")
    if config.system.runtime.background_task_timeout_seconds <= 0:
        issues.append("runtime background_task_timeout_seconds must be positive")

    for employee_id, employee in config.employees.items():
        if employee.default_provider not in config.providers:
            issues.append(
                f"employee {employee_id} references unknown provider {employee.default_provider}"
            )
        if len(set(employee.allowed_tools)) != len(employee.allowed_tools):
            issues.append(f"employee {employee_id} has duplicate allowed tools")
        if len(set(employee.skill_packs)) != len(employee.skill_packs):
            issues.append(f"employee {employee_id} has duplicate skill packs")
        for tool_name in employee.allowed_tools:
            if not is_known_tool(tool_name):
                issues.append(f"employee {employee_id} references unknown tool {tool_name}")
    return issues
