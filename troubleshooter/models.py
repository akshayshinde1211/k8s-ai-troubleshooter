"""Small data structures shared by collection, rules, and output."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ContainerEvidence:
    name: str
    ready: bool
    restart_count: int
    state: str
    waiting_reason: str | None = None
    waiting_message: str | None = None
    termination_reason: str | None = None
    exit_code: int | None = None


@dataclass
class PodEvidence:
    name: str
    namespace: str
    phase: str
    node_name: str | None
    conditions: list[dict[str, str | None]]
    containers: list[ContainerEvidence]
    owners: list[str]
    workload_context: list[str]
    events: list[str]
    configured_images: dict[str, str]
    resource_requests: dict[str, dict[str, str]]
    logs: dict[str, str]
    previous_logs: dict[str, str]
    log_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class RuleResult:
    category: str
    summary: str
    evidence: list[str]
    investigation_steps: list[str]
    commands: list[str]


@dataclass
class AiResult:
    text: str | None = None
    error: str | None = None
