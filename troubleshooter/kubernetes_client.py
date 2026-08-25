"""Kubernetes client setup and narrowly scoped API helpers."""

from __future__ import annotations

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


def load_kubernetes_configuration() -> str:
    """Load kubeconfig first, then fall back to in-cluster authentication."""
    try:
        config.load_kube_config()
        return "kubeconfig"
    except ConfigException:
        try:
            config.load_incluster_config()
            return "in-cluster service account"
        except ConfigException as error:
            raise ConfigException(
                "Unable to load local kubeconfig or in-cluster service account credentials."
            ) from error


def get_core_api() -> client.CoreV1Api:
    return client.CoreV1Api()


def get_apps_api() -> client.AppsV1Api:
    return client.AppsV1Api()


def list_pods(core_api: client.CoreV1Api, namespace: str | None):
    if namespace:
        return core_api.list_namespaced_pod(namespace=namespace).items
    return core_api.list_pod_for_all_namespaces().items
