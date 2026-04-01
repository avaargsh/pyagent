"""Tool commands."""

from __future__ import annotations

from digital_employee.api.cli.common import resolve_json_input


def register(subparsers) -> None:
    parser = subparsers.add_parser("tool", help="Inspect registered tools.")
    tool_subparsers = parser.add_subparsers(dest="tool_action")

    list_parser = tool_subparsers.add_parser("list", help="List tools.")
    list_parser.set_defaults(handler=handle_list, command_name="tool list")

    show_parser = tool_subparsers.add_parser("show", help="Show a tool.")
    show_parser.add_argument("tool_name")
    show_parser.set_defaults(handler=handle_show, command_name="tool show")

    dry_run_parser = tool_subparsers.add_parser("dry-run", help="Validate a tool plan.")
    dry_run_parser.add_argument("tool_name")
    dry_run_parser.add_argument("--employee", required=True)
    dry_run_parser.add_argument("--input", dest="input_text")
    dry_run_parser.add_argument("--input-file")
    dry_run_parser.set_defaults(handler=handle_dry_run, command_name="tool dry-run")


def handle_list(args, context):
    return context.queries.list_tools()


def handle_show(args, context):
    return context.queries.show_tool(args.tool_name)


def handle_dry_run(args, context):
    payload = resolve_json_input(args, required=True, prompt_label="Enter tool payload JSON")
    return context.commands.dry_run_tool(
        tool_name=args.tool_name,
        employee_id=args.employee,
        payload=payload,
    )
