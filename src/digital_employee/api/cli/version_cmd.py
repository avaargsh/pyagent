"""Version command."""

from __future__ import annotations

from digital_employee import __version__
from digital_employee.application.dto.common import CommandResult


def register(subparsers) -> None:
    parser = subparsers.add_parser("version", help="Show CLI version.")
    parser.set_defaults(handler=handle_version, command_name="version")


def handle_version(args, context):
    return CommandResult(
        command="version",
        data={"version": __version__},
        human_lines=[f"dectl version {__version__}"],
    )
