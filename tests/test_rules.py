from troubleshooter.models import ContainerEvidence, PodEvidence
from troubleshooter.rules import analyze_pod


def make_pod(**overrides) -> PodEvidence:
    values = {
        "name": "demo-pod",
        "namespace": "default",
        "phase": "Running",
        "node_name": "worker-1",
        "conditions": [],
        "containers": [],
        "owners": [],
        "workload_context": [],
        "events": [],
        "configured_images": {},
        "resource_requests": {},
        "logs": {},
        "previous_logs": {},
    }
    values.update(overrides)
    return PodEvidence(**values)


def test_crashloop_is_application_runtime():
    pod = make_pod(
        containers=[
            ContainerEvidence(
                name="api",
                ready=False,
                restart_count=4,
                state="waiting",
                waiting_reason="CrashLoopBackOff",
            )
        ]
    )

    result = analyze_pod(pod)

    assert result.category == "APPLICATION_RUNTIME"
    assert "--previous" in " ".join(result.commands)


def test_image_pull_failure_is_image_category():
    pod = make_pod(
        phase="Pending",
        containers=[
            ContainerEvidence(
                name="api",
                ready=False,
                restart_count=0,
                state="waiting",
                waiting_reason="ImagePullBackOff",
            )
        ],
        configured_images={"api": "nginx:this-tag-does-not-exist"},
    )

    result = analyze_pod(pod)

    assert result.category == "IMAGE"
    assert "nginx:this-tag-does-not-exist" in " ".join(result.evidence)


def test_unschedulable_pending_pod_is_scheduling_category():
    pod = make_pod(
        phase="Pending",
        conditions=[
            {
                "type": "PodScheduled",
                "status": "False",
                "reason": "Unschedulable",
                "message": "Insufficient memory",
            }
        ],
        resource_requests={"api": {"cpu": "128", "memory": "512Gi"}},
    )

    result = analyze_pod(pod)

    assert result.category == "SCHEDULING"
    assert "512Gi" in " ".join(result.evidence)


def test_oomkilled_is_resource_category():
    pod = make_pod(
        containers=[
            ContainerEvidence(
                name="api",
                ready=False,
                restart_count=1,
                state="terminated",
                termination_reason="OOMKilled",
                exit_code=137,
            )
        ]
    )

    assert analyze_pod(pod).category == "RESOURCE"
