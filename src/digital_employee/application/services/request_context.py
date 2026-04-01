"""Compatibility wrappers around the new control-plane container."""

from __future__ import annotations

from pathlib import Path

from digital_employee.bootstrap.container import AppContext, build_control_plane_container
from digital_employee.application.services.deps import Deps


def build_app_context(
    root_path: Path,
    profile: str | None = None,
    tenant: str | None = None,
    base_url_override: str | None = None,
    timeout_override: int | None = None,
    output_json: bool = False,
    no_input: bool = False,
) -> AppContext:
    return build_control_plane_container(
        root_path=root_path,
        profile=profile,
        tenant=tenant,
        base_url_override=base_url_override,
        timeout_override=timeout_override,
        output_json=output_json,
        no_input=no_input,
    )


def build_deps(
    root_path: Path,
    profile: str | None = None,
    tenant: str | None = None,
    base_url_override: str | None = None,
    timeout_override: int | None = None,
    output_json: bool = False,
    no_input: bool = False,
) -> Deps:
    return build_app_context(
        root_path=root_path,
        profile=profile,
        tenant=tenant,
        base_url_override=base_url_override,
        timeout_override=timeout_override,
        output_json=output_json,
        no_input=no_input,
    ).deps
