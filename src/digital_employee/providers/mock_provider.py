"""Mock provider implementation."""

from __future__ import annotations

import asyncio
import re

from digital_employee.providers.models import CompletionRequest, CompletionResult


class MockProvider:
    def __init__(self, name: str = "mock", model: str = "mock-default") -> None:
        self.name = name
        self.model = model

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        employee_id = request.metadata.get("employee_id", "unknown")
        exposed_tools = request.metadata.get("exposed_tools", [])
        tool_names = [
            item["name"] if isinstance(item, dict) else str(item)
            for item in exposed_tools
        ] or request.metadata.get("allowed_tools", [])
        prompt_lower = request.prompt.lower()
        if "slow-run" in prompt_lower:
            await asyncio.sleep(0.3)
        if request.metadata.get("tool_observations"):
            return CompletionResult(
                text=(
                    f"Mock plan for {employee_id}: completed '{request.prompt}' after using "
                    f"{', '.join(item['tool_name'] for item in request.metadata['tool_observations'])}."
                ),
                usage={
                    "input_tokens": len(request.prompt.split()),
                    "output_tokens": 12,
                },
            )
        if "send-email" in tool_names and ("send email" in prompt_lower or " email " in f" {prompt_lower} "):
            recipient = _extract_email(request.prompt) or "customer@example.com"
            return CompletionResult(
                text=f"Mock plan for {employee_id}: approval is needed before sending an email.",
                tool_calls=[
                    {
                        "tool_name": "send-email",
                        "payload": {
                            "recipient": recipient,
                            "subject": "Customer follow-up",
                            "body": request.prompt,
                        },
                    }
                ],
                usage={
                    "input_tokens": len(request.prompt.split()),
                    "output_tokens": 11,
                },
            )
        tools = ", ".join(tool_names) or "no tools"
        skills = ", ".join(request.metadata.get("skill_packs", [])) or "no skills"
        text = (
            f"Mock plan for {employee_id}: handle '{request.prompt}' using {skills}; "
            f"allowed tools: {tools}."
        )
        return CompletionResult(
            text=text,
            usage={
                "input_tokens": len(request.prompt.split()),
                "output_tokens": len(text.split()),
            },
        )


def _extract_email(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None
