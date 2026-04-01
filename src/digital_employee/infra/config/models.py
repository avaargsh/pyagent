"""Configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RuntimeConfig:
    default_timeout_seconds: int = 30
    max_retry_count: int = 3
    default_budget_tokens: int = 12000
    max_context_tokens: int = 2000
    recent_message_window: int = 6
    compaction_target_tokens: int = 400
    background_task_timeout_seconds: int = 900


@dataclass(slots=True)
class APIConfig:
    base_url: str = "http://localhost:8000"
    request_timeout_seconds: int = 30


@dataclass(slots=True)
class CLIConfig:
    default_output: str = "human"
    no_input: bool = False


@dataclass(slots=True)
class ObservabilityConfig:
    enable_tracing: bool = True
    redact_secrets: bool = True


@dataclass(slots=True)
class SystemConfig:
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    api: APIConfig = field(default_factory=APIConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)


@dataclass(slots=True)
class ProviderConfig:
    name: str
    model: str
    timeout_seconds: int = 30
    max_output_tokens: int = 1024
    api_key_env: str = ""


@dataclass(slots=True)
class EmployeeConfig:
    id: str
    display_name: str
    default_provider: str
    skill_packs: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    knowledge_scopes: list[str] = field(default_factory=list)
    approval_policy: str = "manual"


@dataclass(slots=True)
class LoadedConfig:
    system: SystemConfig
    providers: dict[str, ProviderConfig]
    employees: dict[str, EmployeeConfig]
    policies: dict[str, dict]
    profile: str | None = None
    tenant: str | None = None
