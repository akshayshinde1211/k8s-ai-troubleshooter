"""Extract focused pod evidence without serializing entire API objects."""

from __future__ import annotations

from kubernetes.client.exceptions import ApiException

from .models import ContainerEvidence, PodEvidence

MAX_LOG_CHARS = 6_000
EVENT_MESSAGE_CHARS = 500


def _trim(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}\n... [truncated]"


def _container_evidence(container_status) -> ContainerEvidence:
    state = container_status.state
    if state is None:
        return ContainerEvidence(
            name=container_status.name,
            ready=container_status.ready,
            restart_count=container_status.restart_count,
            state="unknown",
        )
    if state.waiting:
        return ContainerEvidence(
            name=container_status.name,
            ready=container_status.ready,
            restart_count=container_status.restart_count,
            state="waiting",
            waiting_reason=state.waiting.reason,
            waiting_message=state.waiting.message,
        )
    if state.terminated:
        return ContainerEvidence(
            name=container_status.name,
            ready=container_status.ready,
            restart_count=container_status.restart_count,
            state="terminated",
            termination_reason=state.terminated.reason,
            exit_code=state.terminated.exit_code,
        )
    return ContainerEvidence(
        name=container_status.name,
        ready=container_status.ready,
        restart_count=container_status.restart_count,
        state="running" if state.running else "unknown",
    )


def _conditions(pod) -> list[dict[str, str | None]]:
    return [
        {
            "type": condition.type,
            "status": condition.status,
            "reason": condition.reason,
            "message": condition.message,
        }
        for condition in pod.status.conditions or []
    ]


def _event_summary(event) -> str:
    timestamp = event.event_time or event.last_timestamp or event.metadata.creation_timestamp
    timestamp_text = timestamp.isoformat() if timestamp else "unknown-time"
    return _trim(
        f"{timestamp_text} {event.type or 'Normal'} {event.reason or 'Unknown'}: "
        f"{event.message or ''}",
        EVENT_MESSAGE_CHARS,
    )


def _pod_events(core_api, pod) -> list[str]:
    try:
        event_list = core_api.list_namespaced_event(
            namespace=pod.metadata.namespace,
            field_selector=(
                f"involvedObject.kind=Pod,involvedObject.name={pod.metadata.name}"
            ),
        )
    except ApiException:
        return []

    events = sorted(
        event_list.items,
        key=lambda event: str(
            event.event_time or event.last_timestamp or event.metadata.creation_timestamp
        ),
    )
    return [_event_summary(event) for event in events[-10:]]


def _workload_context(apps_api, pod) -> list[str]:
    context: list[str] = []
    for owner in pod.metadata.owner_references or []:
        if owner.kind != "ReplicaSet":
            continue
        try:
            replica_set = apps_api.read_namespaced_replica_set(
                name=owner.name, namespace=pod.metadata.namespace
            )
        except ApiException:
            continue
        for replica_set_owner in replica_set.metadata.owner_references or []:
            context.append(f"{replica_set_owner.kind}/{replica_set_owner.name}")
    return context


def _collect_logs(core_api, pod, containers: list[ContainerEvidence]):
    logs: dict[str, str] = {}
    previous_logs: dict[str, str] = {}
    errors: list[str] = []

    for container in containers:
        try:
            current = core_api.read_namespaced_pod_log(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                container=container.name,
                tail_lines=100,
                timestamps=True,
            )
            logs[container.name] = _trim(current, MAX_LOG_CHARS)
        except ApiException as error:
            errors.append(f"Current logs for {container.name}: {error.reason}")

        if container.restart_count == 0:
            continue
        try:
            previous = core_api.read_namespaced_pod_log(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                container=container.name,
                tail_lines=100,
                timestamps=True,
                previous=True,
            )
            previous_logs[container.name] = _trim(previous, MAX_LOG_CHARS)
        except ApiException as error:
            errors.append(f"Previous logs for {container.name}: {error.reason}")

    return logs, previous_logs, errors


def _configured_images(pod) -> dict[str, str]:
    return {
        container.name: container.image
        for container in pod.spec.containers or []
        if container.image
    }


def _resource_requests(pod) -> dict[str, dict[str, str]]:
    requests: dict[str, dict[str, str]] = {}
    for container in pod.spec.containers or []:
        if container.resources and container.resources.requests:
            requests[container.name] = dict(container.resources.requests)
    return requests


def collect_pod_evidence(core_api, apps_api, pod) -> PodEvidence:
    """Collect the minimum useful evidence for diagnosis of one pod."""
    statuses = (pod.status.init_container_statuses or []) + (
        pod.status.container_statuses or []
    )
    containers = [_container_evidence(status) for status in statuses]
    logs, previous_logs, log_errors = _collect_logs(core_api, pod, containers)
    owners = [
        f"{owner.kind}/{owner.name}" for owner in pod.metadata.owner_references or []
    ]

    return PodEvidence(
        name=pod.metadata.name,
        namespace=pod.metadata.namespace,
        phase=pod.status.phase,
        node_name=pod.spec.node_name,
        conditions=_conditions(pod),
        containers=containers,
        owners=owners,
        workload_context=_workload_context(apps_api, pod),
        events=_pod_events(core_api, pod),
        configured_images=_configured_images(pod),
        resource_requests=_resource_requests(pod),
        logs=logs,
        previous_logs=previous_logs,
        log_errors=log_errors,
    )
