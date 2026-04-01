"""Tests for FileWorkOrderRepository — tenant isolation and concurrency."""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from digital_employee.domain.work_order import WorkOrder
from digital_employee.infra.repositories.work_orders import FileWorkOrderRepository


class TenantIsolationTest(unittest.TestCase):
    def test_different_tenants_see_different_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_a = FileWorkOrderRepository(root, tenant="tenant-a")
            repo_b = FileWorkOrderRepository(root, tenant="tenant-b")

            wo_a = WorkOrder.create_new(
                employee_id="emp1", input_text="task for A", budget_tokens=100, tenant="tenant-a",
            )
            repo_a.create(wo_a)

            wo_b = WorkOrder.create_new(
                employee_id="emp1", input_text="task for B", budget_tokens=100, tenant="tenant-b",
            )
            repo_b.create(wo_b)

            self.assertEqual(len(repo_a.list_all()), 1)
            self.assertEqual(repo_a.list_all()[0].work_order_id, wo_a.work_order_id)

            self.assertEqual(len(repo_b.list_all()), 1)
            self.assertEqual(repo_b.list_all()[0].work_order_id, wo_b.work_order_id)

            self.assertIsNone(repo_a.get(wo_b.work_order_id))
            self.assertIsNone(repo_b.get(wo_a.work_order_id))

    def test_default_tenant_is_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_default = FileWorkOrderRepository(root, tenant=None)
            repo_named = FileWorkOrderRepository(root, tenant="acme")

            wo = WorkOrder.create_new(
                employee_id="emp1", input_text="default", budget_tokens=100, tenant=None,
            )
            repo_default.create(wo)

            self.assertEqual(len(repo_default.list_all()), 1)
            self.assertEqual(len(repo_named.list_all()), 0)


class ConcurrencyTest(unittest.TestCase):
    def test_concurrent_creates_no_lost_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = FileWorkOrderRepository(root, tenant="concurrent")
            errors: list[Exception] = []
            count = 20

            def _create(idx: int) -> None:
                try:
                    wo = WorkOrder.create_new(
                        employee_id="emp1",
                        input_text=f"task {idx}",
                        budget_tokens=100,
                        tenant="concurrent",
                    )
                    repo.create(wo)
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=_create, args=(i,)) for i in range(count)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [])
            self.assertEqual(len(repo.list_all()), count)


if __name__ == "__main__":
    unittest.main()
