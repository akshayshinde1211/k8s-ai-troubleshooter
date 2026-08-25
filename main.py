"""Command-line entry point for Kubernetes connectivity checks."""

from __future__ import annotations

import argparse
import sys

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException


def load_kubernetes_configuration() -> None:
    """Load the active local kubeconfig used by kubectl."""
    config.load_kube_config()


def check_connectivity() -> int:
    """Verify Kubernetes API access and display a small pod summary."""
    try:
        load_kubernetes_configuration()
        core_api = client.CoreV1Api()
        pod_list = core_api.list_pod_for_all_namespaces(limit=10)
    except ConfigException as error:
        print("Could not load a Kubernetes kubeconfig.")
        print(f"Details: {error}")
        return 1
    except ApiException as error:
        print("Connected configuration could not access the Kubernetes API.")
        print(f"Status: {error.status}")
        print(f"Reason: {error.reason}")
        return 1

    print("Kubernetes API connectivity check succeeded.")
    print(f"Retrieved {len(pod_list.items)} pod(s) in this response.")

    for pod in pod_list.items:
        print(f"- {pod.metadata.namespace}/{pod.metadata.name}: {pod.status.phase}")

    if pod_list.metadata._continue:
        print("Additional pods exist but are not shown in this initial response.")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify connectivity to the current Kubernetes cluster."
    )
    parser.add_argument(
        "command",
        choices=["check-connectivity"],
        help="Run the Kubernetes API connectivity check.",
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()

    if arguments.command == "check-connectivity":
        return check_connectivity()

    return 1


if __name__ == "__main__":
    sys.exit(main())
