"""Domain enums."""

from __future__ import annotations

from enum import StrEnum


class WorkOrderStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_HUMAN = "waiting_human"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SessionStatus(StrEnum):
    OPEN = "open"
    STREAMING = "streaming"
    PAUSED = "paused"
    CLOSED = "closed"
