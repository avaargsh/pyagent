"""Bootstrap file-backed work-order repository."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path

from digital_employee.domain.work_order import WorkOrder


class FileWorkOrderRepository:
    def __init__(self, root_path: Path, tenant: str | None = None) -> None:
        state_root = Path(os.getenv("DE_STATE_DIR", root_path / ".de-state"))
        tenant_dir = state_root / (tenant or "_default")
        tenant_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = tenant_dir / "work_orders.json"
        self._tenant = tenant

    def create(self, work_order: WorkOrder) -> WorkOrder:
        return self.save(work_order)

    def save(self, work_order: WorkOrder) -> WorkOrder:
        with self._locked():
            records = self._load()
            records[work_order.work_order_id] = work_order.to_dict()
            self._save(records)
        return work_order

    def get(self, work_order_id: str) -> WorkOrder | None:
        records = self._load()
        payload = records.get(work_order_id)
        if payload is None:
            return None
        return WorkOrder.from_dict(payload)

    def list_all(self) -> list[WorkOrder]:
        records = self._load()
        orders = [WorkOrder.from_dict(payload) for payload in records.values()]
        return sorted(orders, key=lambda item: item.created_at, reverse=True)

    def _load(self) -> dict[str, dict]:
        if not self._file_path.exists():
            return {}
        payload = json.loads(self._file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return payload

    def _save(self, records: dict[str, dict]) -> None:
        temp_path = self._file_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self._file_path)

    def _locked(self) -> _FileLock:
        return _FileLock(self._file_path.with_suffix(".lock"))


class _FileLock:
    """Context manager for advisory file locking via fcntl."""

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path

    def __enter__(self) -> _FileLock:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = self._lock_path.open("w")
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *args: object) -> None:
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        self._fd.close()
