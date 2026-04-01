"""Background task supervision for long-running agent work."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from secrets import token_hex
from typing import Any, Awaitable, Callable


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_task_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"task_{stamp}_{token_hex(3)}"


def new_task_id() -> str:
    return _new_task_id()


@dataclass(slots=True)
class ManagedTask:
    task_id: str
    name: str
    timeout_seconds: int
    status: str = "pending"
    submitted_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    result: Any = None


TaskFactory = Callable[[], Awaitable[Any]]


class TaskSupervisor:
    def __init__(self, *, default_timeout_seconds: int = 900) -> None:
        self._default_timeout_seconds = default_timeout_seconds
        self._tasks: dict[str, ManagedTask] = {}
        self._handles: dict[str, asyncio.Task[ManagedTask]] = {}

    def start(self, name: str, factory: TaskFactory, timeout_seconds: int | None = None) -> ManagedTask:
        timeout = timeout_seconds or self._default_timeout_seconds
        task = ManagedTask(task_id=_new_task_id(), name=name, timeout_seconds=timeout)
        self._tasks[task.task_id] = task
        self._handles[task.task_id] = asyncio.create_task(self._run(task, factory), name=task.task_id)
        return task

    async def wait(self, task_id: str) -> ManagedTask:
        handle = self._handles.get(task_id)
        if handle is None:
            return self._tasks[task_id]
        try:
            return await handle
        finally:
            self._handles.pop(task_id, None)

    def get(self, task_id: str) -> ManagedTask | None:
        return self._tasks.get(task_id)

    def list_all(self) -> list[ManagedTask]:
        return [self._tasks[key] for key in sorted(self._tasks)]

    async def _run(self, task: ManagedTask, factory: TaskFactory) -> ManagedTask:
        task.status = "running"
        task.started_at = _now()
        try:
            task.result = await asyncio.wait_for(factory(), timeout=task.timeout_seconds)
            task.status = "completed"
        except asyncio.TimeoutError:
            task.status = "timed_out"
            task.error = f"task exceeded timeout of {task.timeout_seconds}s"
        except asyncio.CancelledError:
            task.status = "cancelled"
            task.error = "task was cancelled"
            raise
        except Exception as error:
            task.status = "failed"
            task.error = str(error)
        finally:
            task.finished_at = _now()
        return task
