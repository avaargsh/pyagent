"""Runtime cell lifecycle management."""

from __future__ import annotations

from threading import RLock
from typing import Callable

from digital_employee.runtime.cell import RuntimeCell, RuntimeCellKey

RuntimeCellFactory = Callable[[RuntimeCellKey], RuntimeCell]


class RuntimeManager:
    def __init__(
        self,
        *,
        tenant: str | None,
        config_version: str,
        factory: RuntimeCellFactory,
    ) -> None:
        self._tenant = tenant
        self._config_version = config_version
        self._factory = factory
        self._cells: dict[RuntimeCellKey, RuntimeCell] = {}
        self._lock = RLock()

    @property
    def config_version(self) -> str:
        return self._config_version

    def cell_key_for(self, employee_id: str, config_version: str | None = None) -> RuntimeCellKey:
        return RuntimeCellKey(
            tenant=self._tenant,
            employee_id=employee_id,
            config_version=config_version or self._config_version,
        )

    def get_for_employee(self, employee_id: str, *, config_version: str | None = None) -> RuntimeCell:
        return self.get_cell(self.cell_key_for(employee_id, config_version=config_version))

    def get_cell(self, key: RuntimeCellKey) -> RuntimeCell:
        with self._lock:
            cell = self._cells.get(key)
            if cell is None:
                cell = self._factory(key)
                self._cells[key] = cell
            return cell

    def reload_cell(self, key: RuntimeCellKey) -> RuntimeCell:
        with self._lock:
            cell = self._factory(key)
            self._cells[key] = cell
            return cell

    def close_cell(self, key: RuntimeCellKey) -> None:
        with self._lock:
            self._cells.pop(key, None)

    def invalidate_by_tenant(self, tenant: str | None) -> None:
        with self._lock:
            stale = [key for key in self._cells if key.tenant == tenant]
            for key in stale:
                self._cells.pop(key, None)

    def invalidate_by_employee(self, employee_id: str) -> None:
        with self._lock:
            stale = [key for key in self._cells if key.employee_id == employee_id]
            for key in stale:
                self._cells.pop(key, None)
