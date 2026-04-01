"""REST dependency helpers."""

from __future__ import annotations

from pathlib import Path

from digital_employee.application.services.request_context import build_app_context


def get_context():
    return build_app_context(root_path=Path.cwd())
