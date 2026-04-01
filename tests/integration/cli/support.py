from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import time


def mark_background_session_stale(
    state_dir: str,
    work_order_id: str,
    session_id: str,
    *,
    age_seconds: int = 120,
    lease_timeout_seconds: int = 1,
) -> None:
    stale_at = (datetime.now(UTC) - timedelta(seconds=age_seconds)).isoformat()
    session_path = Path(state_dir) / "_default" / "sessions" / f"{session_id}.json"
    projection_path = Path(state_dir) / "_default" / "projections" / "sessions" / f"{session_id}.json"
    work_order_path = Path(state_dir) / "_default" / "work_orders.json"

    session_payload = _read_json_with_retry(session_path)
    _rewrite_stale_session_payload(
        session_payload["session"],
        stale_at,
        lease_timeout_seconds=lease_timeout_seconds,
    )
    session_path.write_text(json.dumps(session_payload, indent=2, sort_keys=True), encoding="utf-8")

    projection_payload = _read_json_with_retry(projection_path)
    _rewrite_stale_session_payload(
        projection_payload["session_data"],
        stale_at,
        lease_timeout_seconds=lease_timeout_seconds,
    )
    projection_payload["status"] = "streaming"
    projection_payload["ended_at"] = None
    projection_payload["current_stage"] = "executing"
    projection_path.write_text(json.dumps(projection_payload, indent=2, sort_keys=True), encoding="utf-8")

    work_orders_payload = _read_json_with_retry(work_order_path)
    work_order_payload = work_orders_payload[work_order_id]
    work_order_payload["status"] = "running"
    work_order_payload["updated_at"] = stale_at
    work_orders_payload[work_order_id] = work_order_payload
    work_order_path.write_text(json.dumps(work_orders_payload, indent=2, sort_keys=True), encoding="utf-8")


def _rewrite_stale_session_payload(
    session_payload: dict,
    stale_at: str,
    *,
    lease_timeout_seconds: int,
) -> None:
    session_payload["status"] = "streaming"
    session_payload["ended_at"] = None
    session_payload["current_stage"] = "executing"
    metadata = session_payload.setdefault("metadata", {})
    metadata["dispatch_mode"] = "background"
    metadata["background_state"] = "running"
    metadata["background_last_heartbeat_at"] = stale_at
    metadata["background_started_at"] = stale_at
    metadata["lease_timeout_seconds"] = lease_timeout_seconds
    metadata.pop("background_finished_at", None)


def _read_json_with_retry(path: Path, *, attempts: int = 20, interval_seconds: float = 0.05):
    for _ in range(attempts):
        if not path.exists():
            time.sleep(interval_seconds)
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            time.sleep(interval_seconds)
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            time.sleep(interval_seconds)
    raise AssertionError(f"failed to read stable JSON from {path}")
