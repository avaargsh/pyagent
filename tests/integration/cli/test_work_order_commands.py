from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.api.cli.main import main
from tests.integration.cli.support import mark_background_session_stale


class CLIWorkOrderCommandsTest(unittest.TestCase):
    def test_create_and_get_work_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Follow up on open quotes",
                        ]
                    )
                self.assertEqual(create_code, 0)
                created = json.loads(create_stdout.getvalue())
                work_order_id = created["data"]["work_order"]["work_order_id"]
                self.assertTrue(created["data"]["work_order"]["config_snapshot_id"])

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                fetched = json.loads(get_stdout.getvalue())
                self.assertEqual(fetched["data"]["work_order"]["work_order_id"], work_order_id)
                self.assertEqual(
                    fetched["data"]["work_order"]["config_snapshot_id"],
                    created["data"]["work_order"]["config_snapshot_id"],
                )

    def test_run_work_order_updates_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Follow up on open quotes",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                run_payload = json.loads(run_stdout.getvalue())
                self.assertEqual(run_payload["data"]["run"]["status"], "completed")

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                fetched = json.loads(get_stdout.getvalue())
                self.assertEqual(fetched["data"]["work_order"]["status"], "completed")
                self.assertTrue(fetched["data"]["work_order"]["last_session_id"])

    def test_coordinated_work_order_exports_coordination_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--coordinated",
                            "--participant",
                            "sales-assistant",
                            "--input",
                            "Prepare a coordinated follow-up plan",
                        ]
                    )
                self.assertEqual(create_code, 0)
                create_payload = json.loads(create_stdout.getvalue())
                work_order = create_payload["data"]["work_order"]
                work_order_id = work_order["work_order_id"]
                self.assertEqual(work_order["execution_mode"], "coordinated")
                self.assertEqual(work_order["coordinator_participants"], ["sales-assistant"])
                self.assertEqual(work_order["coordinator_plan"]["worker_employee_id"], "sales-assistant")

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                session_id = json.loads(run_stdout.getvalue())["data"]["run"]["session_id"]

                export_stdout = io.StringIO()
                with redirect_stdout(export_stdout):
                    export_code = main(["--json", "session", "export", session_id])
                self.assertEqual(export_code, 0)
                export_payload = json.loads(export_stdout.getvalue())
                session = export_payload["data"]["export"]["session"]
                events = export_payload["data"]["export"]["events"]
                coordination = export_payload["data"]["export"]["coordination"]
                self.assertEqual(session["metadata"]["execution_mode"], "coordinated")
                self.assertEqual(session["metadata"]["dispatch_mode"], "foreground")
                self.assertEqual(session["metadata"]["coordinator_employee_id"], "sales-assistant")
                self.assertEqual(session["metadata"]["worker_employee_id"], "sales-assistant")
                self.assertEqual(session["metadata"]["participant_ids"], ["sales-assistant"])
                self.assertEqual(coordination["worker_employee_id"], "sales-assistant")
                self.assertEqual(
                    session["metadata"]["selection_reason"],
                    work_order["coordinator_plan"]["selection_reason"],
                )
                self.assertIn("coordinator.started", [item["event_type"] for item in events])
                self.assertIn("coordinator.worker_selected", [item["event_type"] for item in events])

                list_stdout = io.StringIO()
                with redirect_stdout(list_stdout):
                    list_code = main(["--json", "session", "list", "--work-order", work_order_id])
                self.assertEqual(list_code, 0)
                list_payload = json.loads(list_stdout.getvalue())
                self.assertEqual(
                    list_payload["data"]["sessions"][0]["coordination"]["worker_employee_id"],
                    "sales-assistant",
                )

    def test_coordinated_create_defaults_participant_to_coordinator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--coordinated",
                            "--input",
                            "Prepare a coordinated follow-up plan",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order = json.loads(create_stdout.getvalue())["data"]["work_order"]
                self.assertEqual(work_order["coordinator_participants"], ["sales-assistant"])
                self.assertEqual(
                    work_order["coordinator_plan"]["worker_employee_id"],
                    "sales-assistant",
                )

    def test_coordinated_work_order_routes_email_to_specialist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--coordinated",
                            "--participant",
                            "sales-assistant",
                            "--participant",
                            "outreach-specialist",
                            "--input",
                            "Please send email to jane@example.com with pricing details",
                        ]
                    )
                self.assertEqual(create_code, 0)
                created_work_order = json.loads(create_stdout.getvalue())["data"]["work_order"]
                work_order_id = created_work_order["work_order_id"]
                self.assertEqual(
                    created_work_order["coordinator_plan"]["worker_employee_id"],
                    "outreach-specialist",
                )

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                run_payload = json.loads(run_stdout.getvalue())
                self.assertEqual(run_payload["data"]["approval"]["status"], "waiting_approval")
                session_id = run_payload["data"]["run"]["session_id"]

                export_stdout = io.StringIO()
                with redirect_stdout(export_stdout):
                    export_code = main(["--json", "session", "export", session_id])
                self.assertEqual(export_code, 0)
                export_payload = json.loads(export_stdout.getvalue())
                session = export_payload["data"]["export"]["session"]
                events = export_payload["data"]["export"]["events"]
                coordination = export_payload["data"]["export"]["coordination"]
                self.assertEqual(session["metadata"]["worker_employee_id"], "outreach-specialist")
                self.assertIn("send-email", session["metadata"]["required_tools"])
                self.assertEqual(coordination["worker_employee_id"], "outreach-specialist")
                self.assertIn("send-email", coordination["required_tools"])
                self.assertEqual(
                    session["metadata"]["selection_reason"],
                    created_work_order["coordinator_plan"]["selection_reason"],
                )
                worker_events = [
                    item for item in events
                    if item["event_type"] == "coordinator.worker_selected"
                ]
                self.assertEqual(worker_events[0]["payload"]["worker_employee_id"], "outreach-specialist")

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                fetched_work_order = json.loads(get_stdout.getvalue())["data"]["work_order"]
                self.assertEqual(
                    fetched_work_order["coordinator_plan"]["worker_employee_id"],
                    "outreach-specialist",
                )

                list_stdout = io.StringIO()
                with redirect_stdout(list_stdout):
                    list_code = main(["--json", "session", "list", "--work-order", work_order_id])
                self.assertEqual(list_code, 0)
                listed_session = json.loads(list_stdout.getvalue())["data"]["sessions"][0]
                self.assertEqual(
                    listed_session["coordination"]["worker_employee_id"],
                    "outreach-specialist",
                )

    def test_work_order_artifacts_returns_summary_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Draft a concise follow-up summary",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                with redirect_stdout(io.StringIO()):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)

                artifacts_stdout = io.StringIO()
                with redirect_stdout(artifacts_stdout):
                    artifacts_code = main(["--json", "work-order", "artifacts", work_order_id])
                self.assertEqual(artifacts_code, 0)
                payload = json.loads(artifacts_stdout.getvalue())
                artifacts = payload["data"]["artifacts"]
                self.assertEqual(len(artifacts), 1)
                self.assertEqual(artifacts[0]["kind"], "summary")
                self.assertTrue(Path(artifacts[0]["uri"]).exists())

    def test_cancel_background_work_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Run a slow-run background planning task",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                with redirect_stdout(io.StringIO()):
                    run_code = main(["--json", "work-order", "run", work_order_id, "--background"])
                self.assertEqual(run_code, 0)

                cancel_stdout = io.StringIO()
                with redirect_stdout(cancel_stdout):
                    cancel_code = main(["--json", "--yes", "work-order", "cancel", work_order_id])
                self.assertEqual(cancel_code, 0)
                cancel_payload = json.loads(cancel_stdout.getvalue())
                self.assertEqual(cancel_payload["data"]["status"], "cancelled")

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                get_payload = json.loads(get_stdout.getvalue())
                self.assertEqual(get_payload["data"]["work_order"]["status"], "cancelled")

                watch_stdout = io.StringIO()
                with redirect_stdout(watch_stdout):
                    watch_code = main(["--json", "work-order", "watch", work_order_id])
                self.assertEqual(watch_code, 0)
                events = json.loads(watch_stdout.getvalue())["data"]["events"]
                self.assertIn("work-order.cancelled", [item["event_type"] for item in events])

    def test_cancel_waiting_approval_expires_pending_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Please send email to jane@example.com about pricing",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id])
                self.assertEqual(run_code, 0)
                approval_id = json.loads(run_stdout.getvalue())["data"]["approval"]["approval_id"]

                cancel_stdout = io.StringIO()
                with redirect_stdout(cancel_stdout):
                    cancel_code = main(["--json", "--yes", "work-order", "cancel", work_order_id])
                self.assertEqual(cancel_code, 0)
                cancel_payload = json.loads(cancel_stdout.getvalue())
                self.assertEqual(cancel_payload["data"]["approval_id"], approval_id)

                approval_stdout = io.StringIO()
                with redirect_stdout(approval_stdout):
                    approval_code = main(["--json", "approval", "get", approval_id])
                self.assertEqual(approval_code, 0)
                approval_payload = json.loads(approval_stdout.getvalue())
                self.assertEqual(approval_payload["data"]["approval"]["status"], "expired")

    def test_cancel_requires_confirmation_outside_tty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Run a slow-run background planning task",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                with redirect_stdout(io.StringIO()):
                    run_code = main(["--json", "work-order", "run", work_order_id, "--background"])
                self.assertEqual(run_code, 0)

                stdout = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                    cancel_code = main(["--json", "work-order", "cancel", work_order_id])
                self.assertEqual(cancel_code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["error"]["type"], "confirmation_required")

    def test_reclaim_stale_background_work_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Prepare a customer follow-up plan",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id, "--background"])
                self.assertEqual(run_code, 0)
                session_id = json.loads(run_stdout.getvalue())["data"]["run"]["session_id"]

                with redirect_stdout(io.StringIO()):
                    tail_code = main(["--jsonl", "session", "tail", session_id, "--follow"])
                self.assertEqual(tail_code, 0)

                self.assertEqual(_wait_for_work_order_status(work_order_id), "completed")
                mark_background_session_stale(temp_dir, work_order_id, session_id)
                self.assertEqual(_wait_for_background_heartbeat_status(session_id), "stale")

                reclaim_stdout = io.StringIO()
                with redirect_stdout(reclaim_stdout):
                    reclaim_code = main(["--json", "--yes", "work-order", "reclaim", work_order_id])
                self.assertEqual(reclaim_code, 0)
                reclaim_payload = json.loads(reclaim_stdout.getvalue())
                self.assertEqual(reclaim_payload["data"]["status"], "failed")
                self.assertEqual(reclaim_payload["data"]["session_id"], session_id)

                get_stdout = io.StringIO()
                with redirect_stdout(get_stdout):
                    get_code = main(["--json", "work-order", "get", work_order_id])
                self.assertEqual(get_code, 0)
                get_payload = json.loads(get_stdout.getvalue())
                self.assertEqual(get_payload["data"]["work_order"]["status"], "failed")
                self.assertEqual(
                    get_payload["data"]["work_order"]["last_error"],
                    "background lease expired; work order reclaimed by the operator",
                )
                self.assertEqual(get_payload["data"]["background"]["state"], "failed")
                self.assertEqual(get_payload["data"]["background"]["heartbeat_status"], "stopped")

                session_stdout = io.StringIO()
                with redirect_stdout(session_stdout):
                    session_code = main(["--json", "session", "get", session_id])
                self.assertEqual(session_code, 0)
                session_payload = json.loads(session_stdout.getvalue())
                self.assertEqual(session_payload["data"]["session"]["status"], "closed")
                self.assertEqual(session_payload["data"]["session"]["current_stage"], "reclaimed")
                self.assertEqual(session_payload["data"]["background"]["state"], "failed")

                watch_stdout = io.StringIO()
                with redirect_stdout(watch_stdout):
                    watch_code = main(["--json", "work-order", "watch", work_order_id])
                self.assertEqual(watch_code, 0)
                watch_payload = json.loads(watch_stdout.getvalue())
                self.assertEqual(watch_payload["data"]["background"]["state"], "failed")
                self.assertIn("work-order.reclaimed", [item["event_type"] for item in watch_payload["data"]["events"]])

    def test_reclaim_requires_confirmation_outside_tty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DE_STATE_DIR": temp_dir}, clear=False):
                create_stdout = io.StringIO()
                with redirect_stdout(create_stdout):
                    create_code = main(
                        [
                            "--json",
                            "work-order",
                            "create",
                            "--employee",
                            "sales-assistant",
                            "--input",
                            "Prepare a customer follow-up plan",
                        ]
                    )
                self.assertEqual(create_code, 0)
                work_order_id = json.loads(create_stdout.getvalue())["data"]["work_order"]["work_order_id"]

                run_stdout = io.StringIO()
                with redirect_stdout(run_stdout):
                    run_code = main(["--json", "work-order", "run", work_order_id, "--background"])
                self.assertEqual(run_code, 0)
                session_id = json.loads(run_stdout.getvalue())["data"]["run"]["session_id"]

                with redirect_stdout(io.StringIO()):
                    tail_code = main(["--jsonl", "session", "tail", session_id, "--follow"])
                self.assertEqual(tail_code, 0)

                self.assertEqual(_wait_for_work_order_status(work_order_id), "completed")
                mark_background_session_stale(temp_dir, work_order_id, session_id)
                self.assertEqual(_wait_for_background_heartbeat_status(session_id), "stale")

                stdout = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                    reclaim_code = main(["--json", "work-order", "reclaim", work_order_id])
                self.assertEqual(reclaim_code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["error"]["type"], "confirmation_required")


def _wait_for_background_heartbeat_status(session_id: str, *, attempts: int = 20, interval_seconds: float = 0.05) -> str | None:
    status = None
    for _ in range(attempts):
        session_stdout = io.StringIO()
        with redirect_stdout(session_stdout):
            session_code = main(["--json", "session", "get", session_id])
        if session_code == 0:
            payload = json.loads(session_stdout.getvalue())
            background = payload["data"].get("background")
            status = None if background is None else background.get("heartbeat_status")
            if status == "stale":
                return status
        time.sleep(interval_seconds)
    return status


def _wait_for_work_order_status(work_order_id: str, *, attempts: int = 20, interval_seconds: float = 0.05) -> str | None:
    status = None
    for _ in range(attempts):
        work_order_stdout = io.StringIO()
        with redirect_stdout(work_order_stdout):
            work_order_code = main(["--json", "work-order", "get", work_order_id])
        if work_order_code == 0:
            payload = json.loads(work_order_stdout.getvalue())
            status = payload["data"]["work_order"]["status"]
            if status == "completed":
                return status
        time.sleep(interval_seconds)
    return status


if __name__ == "__main__":
    unittest.main()
