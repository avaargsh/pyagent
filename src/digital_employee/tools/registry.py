"""Tool registry."""

from __future__ import annotations

from typing import Awaitable, Callable

from digital_employee.domain.errors import ToolNotFoundError
from digital_employee.domain.tool_call import ToolObservation
from digital_employee.tools.models import ToolDefinition


class ToolRegistry:
    """Registry for tool definitions."""

    def __init__(self, tools: list[ToolDefinition] | None = None) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def require(self, name: str) -> ToolDefinition:
        tool = self.get(name)
        if tool is None:
            raise ToolNotFoundError(name)
        return tool

    def list_all(self) -> list[ToolDefinition]:
        return [self._tools[key] for key in sorted(self._tools)]

    def filter_by_names(self, names: list[str]) -> list[ToolDefinition]:
        return [self._tools[name] for name in names if name in self._tools]


async def _knowledge_search(payload: dict[str, object]) -> ToolObservation:
    query = str(payload.get("query", "")).strip()
    scope = str(payload.get("scope", "general"))
    summary = f"knowledge hit for '{query or 'general guidance'}' in scope {scope}"
    return ToolObservation(
        tool_name="knowledge-search",
        status="ok",
        payload={
            "query": query,
            "scope": scope,
            "matches": [summary],
        },
    )


async def _send_email(payload: dict[str, object]) -> ToolObservation:
    recipient = str(payload.get("recipient") or payload.get("to") or "unknown@example.com")
    subject = str(payload.get("subject", "")).strip()
    return ToolObservation(
        tool_name="send-email",
        status="dry_run",
        payload={
            "recipient": recipient,
            "subject": subject,
            "queued": False,
        },
    )


async def _dry_run(payload: dict[str, object]) -> ToolObservation:
    return ToolObservation(
        tool_name="dry-run",
        status="ok",
        payload={"validated": True, "input": dict(payload)},
    )


ToolBuilder = Callable[[], ToolDefinition]


def _knowledge_search_tool() -> ToolDefinition:
    return ToolDefinition(
        name="knowledge-search",
        description="Search the scoped knowledge base and return a dry-run summary.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scope": {"type": "string"},
            },
            "required": ["query"],
        },
        handler=_knowledge_search,
        resource_kind="knowledge",
        risk_level="low",
        permission_mode="auto",
        side_effects="none",
        is_read_only=True,
        is_concurrency_safe=True,
    )


def _send_email_tool() -> ToolDefinition:
    return ToolDefinition(
        name="send-email",
        description="Prepare an outbound email action as a dry-run observation.",
        input_schema={
            "type": "object",
            "properties": {
                "recipient": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["recipient", "subject"],
        },
        handler=_send_email,
        resource_kind="communication",
        risk_level="high",
        permission_mode="approval_required",
        side_effects="external_email",
        requires_approval=True,
    )


def _dry_run_tool() -> ToolDefinition:
    return ToolDefinition(
        name="dry-run",
        description="Validate a tool payload without invoking external side effects.",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=_dry_run,
        resource_kind="diagnostic",
        risk_level="low",
        permission_mode="auto",
        side_effects="none",
        is_read_only=True,
        is_concurrency_safe=True,
    )


_TOOL_BUILDERS: dict[str, ToolBuilder] = {
    "dry-run": _dry_run_tool,
    "knowledge-search": _knowledge_search_tool,
    "send-email": _send_email_tool,
}


def is_known_tool(name: str) -> bool:
    return name in _TOOL_BUILDERS


def build_tool(name: str) -> ToolDefinition:
    builder = _TOOL_BUILDERS.get(name)
    if builder is None:
        raise ToolNotFoundError(name)
    return builder()


def build_tool_registry(names: list[str]) -> ToolRegistry:
    tools = [build_tool(name) for name in sorted(set(names)) if is_known_tool(name)]
    return ToolRegistry(tools=tools)
