"""Control-plane container assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from digital_employee.agents.assembler import assemble_employee_registry
from digital_employee.application.services.deps import Deps
from digital_employee.application.services.facades import CommandFacade, QueryFacade
from digital_employee.bootstrap.factories import (
    build_observability_bundle,
    build_repositories,
    build_runtime_bundle,
    build_runtime_manager,
)
from digital_employee.domain.errors import ConfigError
from digital_employee.infra.config.loader import load_app_config
from digital_employee.infra.config.validate import validate_loaded_config
from digital_employee.runtime.coordinator_runtime import CoordinatorRuntime


@dataclass(slots=True)
class AppContext:
    deps: Deps
    commands: CommandFacade
    queries: QueryFacade

    @property
    def validation_issues(self) -> list[str]:
        return self.deps.validation_issues


def build_control_plane_container(
    root_path: Path,
    profile: str | None = None,
    tenant: str | None = None,
    base_url_override: str | None = None,
    timeout_override: int | None = None,
    output_json: bool = False,
    no_input: bool = False,
) -> AppContext:
    try:
        config = load_app_config(
            root_path=root_path,
            profile=profile,
            tenant=tenant,
            base_url_override=base_url_override,
            timeout_override=timeout_override,
            output_json=output_json,
            no_input=no_input,
        )
        issues = validate_loaded_config(config)
        registry = assemble_employee_registry(config)
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as error:
        raise ConfigError(
            message=f"failed to load configuration: {error}",
            hint="run 'dectl config validate' for details",
        ) from error

    repositories = build_repositories(root_path=root_path, tenant=config.tenant)
    observability_bundle = build_observability_bundle(repositories, config.tenant)
    runtime_bundle = build_runtime_bundle(config, repositories.approval_repo)
    runtime_manager = build_runtime_manager(config, registry, repositories.approval_repo)
    deps = Deps(
        config=config,
        config_version=runtime_manager.config_version,
        validation_issues=issues,
        root_path=root_path,
        work_order_repo=repositories.work_order_repo,
        session_repo=repositories.session_repo,
        approval_repo=repositories.approval_repo,
        event_ledger=observability_bundle.event_ledger,
        projection_store=observability_bundle.projection_store,
        employee_registry=registry,
        provider_catalog=runtime_bundle.provider_catalog,
        provider_factory=runtime_bundle.provider_factory,
        provider_router=runtime_bundle.provider_router,
        hook_dispatcher=runtime_bundle.hook_dispatcher,
        tool_registry=runtime_bundle.tool_registry,
        tool_executor=runtime_bundle.tool_executor,
        context_compactor=runtime_bundle.context_compactor,
        tool_exposure_planner=runtime_bundle.tool_exposure_planner,
        policy_engine=runtime_bundle.policy_engine,
        task_supervisor=runtime_bundle.task_supervisor,
        turn_engine=runtime_bundle.turn_engine,
        runtime_manager=runtime_manager,
        coordinator_runtime=CoordinatorRuntime(
            employee_registry=registry,
            runtime_manager=runtime_manager,
        ),
    )
    return AppContext(
        deps=deps,
        commands=CommandFacade(deps),
        queries=QueryFacade(deps),
    )
