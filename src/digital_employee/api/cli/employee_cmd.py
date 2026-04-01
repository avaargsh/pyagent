"""Employee commands."""

from __future__ import annotations

import asyncio

from digital_employee.api.cli.common import resolve_text_input


def register(subparsers) -> None:
    parser = subparsers.add_parser("employee", help="Inspect or test digital employees.")
    employee_subparsers = parser.add_subparsers(dest="employee_action")

    list_parser = employee_subparsers.add_parser("list", help="List employees.")
    list_parser.set_defaults(handler=handle_list, command_name="employee list")

    show_parser = employee_subparsers.add_parser("show", help="Show an employee profile.")
    show_parser.add_argument("employee_id")
    show_parser.set_defaults(handler=handle_show, command_name="employee show")

    test_parser = employee_subparsers.add_parser("test", help="Run a dry-run employee test.")
    test_parser.add_argument("employee_id")
    test_parser.add_argument("--input", dest="input_text")
    test_parser.add_argument("--input-file")
    test_parser.set_defaults(handler=handle_test, command_name="employee test")


def handle_list(args, context):
    return context.queries.list_employees()


def handle_show(args, context):
    return context.queries.show_employee(args.employee_id)


def handle_test(args, context):
    prompt = resolve_text_input(args, required=True, prompt_label="Enter a dry-run task")
    return asyncio.run(context.commands.test_employee(args.employee_id, prompt))
