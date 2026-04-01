"""Config commands."""

from __future__ import annotations

def register(subparsers) -> None:
    parser = subparsers.add_parser("config", help="Inspect effective configuration.")
    config_subparsers = parser.add_subparsers(dest="config_action")

    show_parser = config_subparsers.add_parser("show", help="Show effective configuration.")
    show_parser.set_defaults(handler=handle_show, command_name="config show")

    validate_parser = config_subparsers.add_parser("validate", help="Validate configuration.")
    validate_parser.set_defaults(handler=handle_validate, command_name="config validate")


def handle_show(args, context):
    return context.queries.show_config()


def handle_validate(args, context):
    return context.commands.validate_config()
