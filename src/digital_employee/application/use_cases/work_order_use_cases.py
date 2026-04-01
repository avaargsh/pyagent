"""Compatibility shim for migrated work-order commands and queries."""

from digital_employee.application.commands.work_order_commands import (
    create_work_order,
    execute_work_order_task,
    reclaim_work_order,
    resume_work_order,
    run_work_order,
    start_background_work_order,
)
from digital_employee.application.queries.work_order_queries import (
    get_work_order,
    list_work_order_artifacts,
    list_work_orders,
    resolve_work_order_session_record,
    watch_work_order,
)

__all__ = [
    "create_work_order",
    "execute_work_order_task",
    "get_work_order",
    "list_work_order_artifacts",
    "list_work_orders",
    "reclaim_work_order",
    "resolve_work_order_session_record",
    "resume_work_order",
    "run_work_order",
    "start_background_work_order",
    "watch_work_order",
]
