"""Work-order commands."""

from __future__ import annotations

import asyncio
import argparse
import sys

from digital_employee.api.cli.common import resolve_text_input
from digital_employee.api.cli.event_stream import stream_session_record_events
from digital_employee.application.dto.common import CommandFailure, StreamResult


def register(subparsers) -> None:
    parser = subparsers.add_parser("work-order", help="Create and inspect work orders.")
    work_order_subparsers = parser.add_subparsers(dest="work_order_action")

    create_parser = work_order_subparsers.add_parser("create", help="Create a work order.")
    create_parser.add_argument("--employee", required=True)
    create_parser.add_argument("--input", dest="input_text")
    create_parser.add_argument("--input-file")
    create_parser.add_argument("--budget", type=int)
    create_parser.add_argument("--coordinated", action="store_true")
    create_parser.add_argument("--participant", action="append", dest="participants")
    create_parser.set_defaults(handler=handle_create, command_name="work-order create")

    get_parser = work_order_subparsers.add_parser("get", help="Get a work order.")
    get_parser.add_argument("work_order_id")
    get_parser.set_defaults(handler=handle_get, command_name="work-order get")

    list_parser = work_order_subparsers.add_parser("list", help="List work orders.")
    list_parser.set_defaults(handler=handle_list, command_name="work-order list")

    run_parser = work_order_subparsers.add_parser("run", help="Run a work order.")
    run_parser.add_argument("work_order_id")
    run_parser.add_argument("--background", action="store_true")
    run_parser.set_defaults(handler=handle_run, command_name="work-order run")

    cancel_parser = work_order_subparsers.add_parser("cancel", help="Cancel a running work order.")
    cancel_parser.add_argument("work_order_id")
    cancel_parser.set_defaults(handler=handle_cancel, command_name="work-order cancel")

    reclaim_parser = work_order_subparsers.add_parser(
        "reclaim",
        help="Reclaim a stale background work order.",
    )
    reclaim_parser.add_argument("work_order_id")
    reclaim_parser.add_argument("--reason")
    reclaim_parser.set_defaults(handler=handle_reclaim, command_name="work-order reclaim")

    resume_parser = work_order_subparsers.add_parser("resume", help="Resume a paused work order.")
    resume_parser.add_argument("work_order_id")
    resume_parser.add_argument("--background", action="store_true")
    resume_parser.set_defaults(handler=handle_resume, command_name="work-order resume")

    watch_parser = work_order_subparsers.add_parser("watch", help="Watch work-order events.")
    watch_parser.add_argument("work_order_id")
    watch_parser.add_argument("--follow", action="store_true")
    watch_parser.add_argument("--since")
    watch_parser.add_argument("--level", choices=("info", "warn", "error", "debug"))
    watch_parser.set_defaults(handler=handle_watch, command_name="work-order watch")

    artifacts_parser = work_order_subparsers.add_parser("artifacts", help="List work-order artifacts.")
    artifacts_parser.add_argument("work_order_id")
    artifacts_parser.set_defaults(handler=handle_artifacts, command_name="work-order artifacts")

    execute_parser = work_order_subparsers.add_parser("_execute", help=argparse.SUPPRESS)
    execute_parser.add_argument("work_order_id")
    execute_parser.add_argument("--session-id", required=True)
    execute_parser.add_argument("--task-id", required=True)
    execute_parser.set_defaults(handler=handle_execute, command_name="work-order _execute")


def handle_create(args, context):
    prompt = resolve_text_input(args, required=True, prompt_label="Enter a work order request")
    return context.commands.create_work_order(
        employee_id=args.employee,
        input_text=prompt,
        budget_tokens=args.budget,
        coordinated=args.coordinated or bool(args.participants),
        participant_ids=args.participants,
    )


def handle_get(args, context):
    return context.queries.get_work_order(args.work_order_id)


def handle_list(args, context):
    return context.queries.list_work_orders()


def handle_run(args, context):
    if args.background:
        return context.commands.start_background_work_order(args.work_order_id)
    return asyncio.run(context.commands.run_work_order(args.work_order_id))


def handle_cancel(args, context):
    _confirm_destructive_action(
        args,
        prompt=f"Cancel work order {args.work_order_id}? [y/N]: ",
        message="work-order cancel requires confirmation",
    )
    return context.commands.cancel_work_order(args.work_order_id)


def handle_reclaim(args, context):
    _confirm_destructive_action(
        args,
        prompt=f"Reclaim work order {args.work_order_id}? [y/N]: ",
        message="work-order reclaim requires confirmation",
    )
    return context.commands.reclaim_work_order(args.work_order_id, reason=args.reason)


def handle_resume(args, context):
    if args.background:
        return context.commands.start_background_resume_work_order(args.work_order_id)
    return asyncio.run(context.commands.resume_work_order(args.work_order_id))


def handle_watch(args, context):
    if args.follow or getattr(args, "jsonl", False):
        stream_session_record_events(
            lambda: context.queries.resolve_work_order_session_record(args.work_order_id),
            resource_id=args.work_order_id,
            follow=args.follow,
            since=args.since,
            level=args.level,
            as_jsonl=getattr(args, "jsonl", False),
            payload_factory=lambda record, _event, _level: {"session_id": record.session.session_id},
        )
        return StreamResult(command="work-order watch")
    return context.queries.watch_work_order(args.work_order_id)


def handle_artifacts(args, context):
    return context.queries.list_work_order_artifacts(args.work_order_id)


def handle_execute(args, context):
    return asyncio.run(
        context.commands.execute_work_order_task(
            args.work_order_id,
            session_id=args.session_id,
            task_id=args.task_id,
        )
    )


def _confirm_destructive_action(args, *, prompt: str, message: str) -> None:
    if getattr(args, "yes", False):
        return
    if getattr(args, "no_input", False):
        raise CommandFailure(2, "confirmation_required", message, "pass --yes")
    if sys.stdin.isatty():
        confirmed = input(prompt).strip().lower()
        if confirmed in {"y", "yes"}:
            return
        raise CommandFailure(2, "confirmation_required", message, "pass --yes")
    raise CommandFailure(2, "confirmation_required", message, "pass --yes")
