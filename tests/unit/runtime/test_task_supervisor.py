from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from digital_employee.runtime.task_supervisor import TaskSupervisor


class TaskSupervisorTest(unittest.TestCase):
    def test_background_task_completes(self) -> None:
        async def scenario() -> None:
            supervisor = TaskSupervisor(default_timeout_seconds=1)

            async def work() -> str:
                await asyncio.sleep(0)
                return "done"

            task = supervisor.start("demo", work)
            completed = await supervisor.wait(task.task_id)
            self.assertEqual(completed.status, "completed")
            self.assertEqual(completed.result, "done")

        asyncio.run(scenario())

    def test_background_task_times_out(self) -> None:
        async def scenario() -> None:
            supervisor = TaskSupervisor(default_timeout_seconds=1)

            async def work() -> str:
                await asyncio.sleep(0.01)
                return "late"

            task = supervisor.start("demo", work, timeout_seconds=0.0001)
            completed = await supervisor.wait(task.task_id)
            self.assertEqual(completed.status, "timed_out")
            self.assertIn("timeout", completed.error or "")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
