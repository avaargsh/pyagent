"""File-backed approval repository."""

from __future__ import annotations

import json
import os
from pathlib import Path

from digital_employee.domain.approval import ApprovalRequest
from digital_employee.infra.repositories.work_orders import _FileLock


class FileApprovalRepository:
    def __init__(self, root_path: Path, tenant: str | None = None) -> None:
        state_root = Path(os.getenv("DE_STATE_DIR", root_path / ".de-state"))
        tenant_dir = state_root / (tenant or "_default")
        tenant_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = tenant_dir / "approvals.json"

    def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        return self.save(approval)

    def save(self, approval: ApprovalRequest) -> ApprovalRequest:
        with _FileLock(self._file_path.with_suffix(".lock")):
            records = self._load()
            records[approval.approval_id] = approval.to_dict()
            self._save(records)
        return approval

    def get(self, approval_id: str) -> ApprovalRequest | None:
        records = self._load()
        payload = records.get(approval_id)
        if payload is None:
            return None
        return ApprovalRequest.from_dict(payload)

    def list_all(self) -> list[ApprovalRequest]:
        records = self._load()
        approvals = [ApprovalRequest.from_dict(payload) for payload in records.values()]
        return sorted(approvals, key=lambda item: item.created_at, reverse=True)

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
