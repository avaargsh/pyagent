"""Approval commands."""

from __future__ import annotations

import asyncio
import sys

from digital_employee.api.cli.common import CommandFailure
from digital_employee.application.dto.common import CommandResult

def register(subparsers) -> None:
    parser = subparsers.add_parser("approval", help="Approval control plane commands.")
    approval_subparsers = parser.add_subparsers(dest="approval_action")

    list_parser = approval_subparsers.add_parser("list", help="List approvals.")
    list_parser.add_argument("--status")
    list_parser.set_defaults(handler=handle_list, command_name="approval list")

    get_parser = approval_subparsers.add_parser("get", help="Get an approval.")
    get_parser.add_argument("approval_id")
    get_parser.set_defaults(handler=handle_get, command_name="approval get")

    decide_parser = approval_subparsers.add_parser("decide", help="Approve or reject.")
    decide_parser.add_argument("approval_id")
    decide_parser.add_argument("--decision", choices=["approve", "reject"])
    decide_parser.add_argument("--reason")
    decide_parser.add_argument("--resume", action="store_true")
    decide_parser.add_argument("--background", action="store_true")
    decide_parser.set_defaults(handler=handle_decide, command_name="approval decide")


def handle_list(args, context):
    return context.queries.list_approvals(status=args.status)


def handle_get(args, context):
    return context.queries.get_approval(args.approval_id)


def handle_decide(args, context):
    if args.background and not args.resume:
        raise CommandFailure(
            2,
            "background_requires_resume",
            "approval decide --background requires --resume",
            "pass --resume --background together",
        )
    decision = args.decision
    if not decision:
        if args.no_input:
            raise CommandFailure(2, "decision_required", "approval decision is required", "pass --decision")
        if sys.stdin.isatty():
            decision = input("Decision [approve/reject]: ").strip().lower()
    if decision not in {"approve", "reject"}:
        raise CommandFailure(2, "decision_required", "approval decision is required", "pass --decision")
    if args.resume and decision != "approve":
        raise CommandFailure(
            2,
            "resume_requires_approve",
            "approval decide --resume only supports --decision approve",
            "use --decision approve with --resume, or omit --resume",
        )

    reason = (args.reason or "").strip()
    if not reason:
        raise CommandFailure(
            2,
            "approval_reason_required",
            f"approval {args.approval_id} cannot be approved: reason is required; pass --reason",
        )
    approval_result = context.commands.decide_approval(args.approval_id, decision=decision, reason=reason)
    if not args.resume:
        return approval_result

    approval_data = approval_result.data["approval"]
    work_order_id = approval_data.get("work_order_id")
    if not work_order_id:
        raise CommandFailure(
            7,
            "work_order_not_found",
            f"approval {args.approval_id} has no work order to resume",
        )

    if args.background:
        resume_result = context.commands.start_background_resume_work_order(work_order_id)
    else:
        resume_result = asyncio.run(context.commands.resume_work_order(work_order_id))
    return _combine_decision_and_resume(approval_result, resume_result)


def _combine_decision_and_resume(
    approval_result: CommandResult,
    resume_result: CommandResult,
) -> CommandResult:
    return CommandResult(
        command="approval decide",
        data={
            "approval": approval_result.data["approval"],
            "resume": resume_result.data,
        },
        human_lines=[
            *approval_result.human_lines,
            *resume_result.human_lines,
        ],
    )
