"""Doctor command."""

from __future__ import annotations

def register(subparsers) -> None:
    parser = subparsers.add_parser("doctor", help="Diagnose environment state.")
    parser.set_defaults(handler=handle_doctor, command_name="doctor")


def handle_doctor(args, context):
    return context.queries.run_doctor()
