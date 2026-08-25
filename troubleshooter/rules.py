"""Deterministic Kubernetes failure classification."""

from __future__ import annotations

from .models import PodEvidence, RuleResult


def _pod_commands(pod: PodEvidence) -> list[str]:
    commands = [
        f"kubectl -n {pod.namespace} describe pod {pod.name}",
        (
            f"kubectl -n {pod.namespace} get events "
            f"--field-selector involvedObject.name={pod.name}"
        ),
    ]
    for container in pod.containers:
        commands.append(
            f"kubectl -n {pod.namespace} logs {pod.name} -c {container.name}"
        )
        if container.restart_count:
            commands.append(
                f"kubectl -n {pod.namespace} logs {pod.name} -c {container.name} --previous"
            )
    return commands


def _container_signal(pod: PodEvidence, reason: str) -> list[str]:
    return [
        f"Container {container.name} reports {reason}."
        for container in pod.containers
        if container.waiting_reason == reason
    ]


def _event_contains(pod: PodEvidence, phrase: str) -> bool:
    return any(phrase.lower() in event.lower() for event in pod.events)


def analyze_pod(pod: PodEvidence) -> RuleResult:
    """Classify known signals before any optional AI call."""
    commands = _pod_commands(pod)

    oom_evidence = [
        f"Container {container.name} was terminated with OOMKilled."
        for container in pod.containers
        if container.termination_reason == "OOMKilled"
    ]
    if oom_evidence:
        return RuleResult(
            category="RESOURCE",
            summary="The container exceeded its available memory.",
            evidence=oom_evidence,
            investigation_steps=[
                "Compare the container memory limit with observed application demand.",
                "Review application memory usage and possible memory leaks.",
            ],
            commands=commands,
        )

    config_evidence = _container_signal(pod, "CreateContainerConfigError")
    if config_evidence:
        return RuleResult(
            category="CONFIGURATION",
            summary="Kubernetes could not construct the container from its configuration.",
            evidence=config_evidence + pod.events[-3:],
            investigation_steps=[
                "Verify referenced ConfigMaps, Secrets, keys, volumes, and environment variables.",
                "Read the pod events for the missing or invalid reference.",
            ],
            commands=commands,
        )

    image_evidence = _container_signal(pod, "ImagePullBackOff") + _container_signal(
        pod, "ErrImagePull"
    )
    if image_evidence:
        return RuleResult(
            category="IMAGE",
            summary="Kubernetes cannot pull the configured container image.",
            evidence=image_evidence + pod.events[-3:],
            investigation_steps=[
                "Verify the image name and tag in the workload specification.",
                "Check registry credentials and network access if the image is private.",
            ],
            commands=commands,
        )

    crash_evidence = _container_signal(pod, "CrashLoopBackOff")
    if crash_evidence:
        restarts = [
            f"Container {container.name} has restarted {container.restart_count} time(s)."
            for container in pod.containers
            if container.restart_count
        ]
        return RuleResult(
            category="APPLICATION_RUNTIME",
            summary="The application repeatedly exits during startup or execution.",
            evidence=crash_evidence + restarts + pod.events[-3:],
            investigation_steps=[
                "Inspect previous container logs to find the last failed execution.",
                "Validate application configuration and dependent service availability.",
            ],
            commands=commands,
        )

    unschedulable = any(
        condition["type"] == "PodScheduled"
        and condition["status"] == "False"
        and condition["reason"] == "Unschedulable"
        for condition in pod.conditions
    )
    if pod.phase == "Pending" and (unschedulable or _event_contains(pod, "insufficient")):
        scheduling_events = [
            event for event in pod.events if "insufficient" in event.lower() or "schedul" in event.lower()
        ]
        return RuleResult(
            category="SCHEDULING",
            summary="The pod cannot be scheduled onto an available node.",
            evidence=["Pod phase is Pending."] + scheduling_events[-3:],
            investigation_steps=[
                "Compare requested CPU and memory with allocatable node capacity.",
                "Check node selectors, taints, tolerations, and affinity rules.",
            ],
            commands=commands,
        )

    if _event_contains(pod, "probe failed"):
        return RuleResult(
            category="HEALTH_PROBE",
            summary="Kubernetes reports a failed container health probe.",
            evidence=[event for event in pod.events if "probe failed" in event.lower()][-3:],
            investigation_steps=[
                "Verify the probe path, port, protocol, and timing values.",
                "Confirm the application is listening before probe deadlines expire.",
            ],
            commands=commands,
        )

    restart_evidence = [
        f"Container {container.name} has restarted {container.restart_count} time(s)."
        for container in pod.containers
        if container.restart_count >= 3
    ]
    if restart_evidence:
        return RuleResult(
            category="APPLICATION_RUNTIME",
            summary="The pod has excessive restarts without a more specific Kubernetes reason.",
            evidence=restart_evidence + pod.events[-3:],
            investigation_steps=[
                "Inspect current and previous container logs.",
                "Review exit codes and recent Kubernetes events.",
            ],
            commands=commands,
        )

    return RuleResult(
        category="UNKNOWN",
        summary="The pod has a failure signal that needs further investigation.",
        evidence=[f"Pod phase is {pod.phase}."] + pod.events[-3:],
        investigation_steps=[
            "Inspect pod conditions, events, and container logs.",
            "Collect additional workload and dependency context before changing resources.",
        ],
        commands=commands,
    )
