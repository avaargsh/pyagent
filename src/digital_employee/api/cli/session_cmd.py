"""Session commands."""

from __future__ import annotations

from digital_employee.api.cli.event_stream import stream_session_record_events
from digital_employee.application.dto.common import StreamResult


def register(subparsers) -> None:
    parser = subparsers.add_parser("session", help="Observe execution sessions.")
    session_subparsers = parser.add_subparsers(dest="session_action")

    list_parser = session_subparsers.add_parser("list", help="List sessions.")
    list_parser.add_argument("--work-order")
    list_parser.add_argument("--employee")
    list_parser.add_argument("--status")
    list_parser.set_defaults(handler=handle_list, command_name="session list")

    get_parser = session_subparsers.add_parser("get", help="Get a session summary.")
    get_parser.add_argument("session_id")
    get_parser.set_defaults(handler=handle_get, command_name="session get")

    tail_parser = session_subparsers.add_parser("tail", help="Tail session events.")
    tail_parser.add_argument("session_id")
    tail_parser.add_argument("--follow", action="store_true")
    tail_parser.add_argument("--since")
    tail_parser.add_argument("--level", choices=("info", "warn", "error", "debug"))
    tail_parser.set_defaults(handler=handle_tail, command_name="session tail")

    export_parser = session_subparsers.add_parser("export", help="Export a session record.")
    export_parser.add_argument("session_id")
    export_parser.set_defaults(handler=handle_export, command_name="session export")


def handle_list(args, context):
    return context.queries.list_sessions(
        work_order_id=args.work_order,
        employee_id=args.employee,
        status=args.status,
    )


def handle_get(args, context):
    return context.queries.get_session(args.session_id)


def handle_tail(args, context):
    if args.follow or getattr(args, "jsonl", False):
        stream_session_record_events(
            lambda: context.queries.resolve_session_record(args.session_id),
            resource_id=args.session_id,
            follow=args.follow,
            since=args.since,
            level=args.level,
            as_jsonl=getattr(args, "jsonl", False),
            not_found=(7, "session_not_found", f"session {args.session_id} was not found"),
        )
        return StreamResult(command="session tail")
    return context.queries.tail_session(args.session_id)


def handle_export(args, context):
    return context.queries.export_session(args.session_id)
