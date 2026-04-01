"""Replay commands."""

from __future__ import annotations

from digital_employee.api.cli.common import CommandFailure


def register(subparsers) -> None:
    parser = subparsers.add_parser("replay", help="Replay execution events.")
    replay_subparsers = parser.add_subparsers(dest="replay_action")

    run_parser = replay_subparsers.add_parser("run", help="Replay a work order.")
    run_parser.add_argument("work_order_id")
    run_parser.set_defaults(handler=handle_not_implemented, command_name="replay run")


def handle_not_implemented(args, context):
    raise CommandFailure(1, "not_implemented", f"{args.command_name} is not implemented yet")
