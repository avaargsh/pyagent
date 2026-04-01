"""Tool execution boundary."""

from __future__ import annotations

from digital_employee.domain.errors import DigitalEmployeeError, ToolExecutionError
from digital_employee.domain.tool_call import ToolObservation
from digital_employee.tools.models import ToolDefinition
from digital_employee.tools.schemas import ensure_valid_tool_payload


class ToolExecutor:
    async def execute(self, definition: ToolDefinition, payload: dict) -> ToolObservation:
        ensure_valid_tool_payload(definition.name, definition.input_schema, payload)
        try:
            return await definition.handler(payload)
        except DigitalEmployeeError:
            raise
        except Exception as error:
            raise ToolExecutionError(definition.name, str(error)) from error
