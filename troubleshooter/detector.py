"""Identify pods that have concrete Kubernetes failure signals."""

from __future__ import annotations


WAITING_FAILURE_REASONS = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "CreateContainerConfigError",
    "RunContainerError",
}


def _container_statuses(pod):
    status = pod.status
    return (status.init_container_statuses or []) + (status.container_statuses or [])


def _is_unschedulable(pod) -> bool:
    for condition in pod.status.conditions or []:
        if condition.type == "PodScheduled" and condition.status == "False":
            return condition.reason == "Unschedulable"
    return False


def is_unhealthy(pod, restart_threshold: int = 3) -> bool:
    """Return true only for explicit failure signals, not normal startup states."""
    if pod.status.phase in {"Pending", "Failed"} or _is_unschedulable(pod):
        return True

    for container in _container_statuses(pod):
        state = container.state
        if state is None:
            continue
        if state.waiting and state.waiting.reason in WAITING_FAILURE_REASONS:
            return True
        if state.terminated and state.terminated.reason == "OOMKilled":
            return True
        if container.restart_count >= restart_threshold:
            return True

    return False


def find_unhealthy_pods(pods, restart_threshold: int = 3) -> list:
    """Return each unhealthy pod once, even when it has several symptoms."""
    return [pod for pod in pods if is_unhealthy(pod, restart_threshold)]
