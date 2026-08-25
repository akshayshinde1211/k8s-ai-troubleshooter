"""Read-only CLI for diagnosing unhealthy Kubernetes pods."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException

from troubleshooter.ai_analyzer import (
    DEFAULT_MODEL,
    GeminiConfigurationError,
    analyze_with_gemini,
    require_gemini_api_key,
)
from troubleshooter.collector import collect_pod_evidence
from troubleshooter.detector import find_unhealthy_pods
from troubleshooter.kubernetes_client import (
    get_apps_api,
    get_core_api,
    list_pods,
    load_kubernetes_configuration,
)
from troubleshooter.output import console, print_diagnosis, print_scan_summary
from troubleshooter.rules import analyze_pod


def check_connectivity(namespace: str | None) -> int:
    authentication_source = load_kubernetes_configuration()
    pods = list_pods(get_core_api(), namespace)
    console.print("Kubernetes API connectivity check succeeded.")
    console.print(f"Authentication: {authentication_source}")
    console.print(f"Retrieved {len(pods)} pod(s).")
    return 0


def scan(namespace: str | None, model: str) -> int:
    require_gemini_api_key()
    authentication_source = load_kubernetes_configuration()
    core_api = get_core_api()
    apps_api = get_apps_api()
    pods = list_pods(core_api, namespace)
    unhealthy_pods = find_unhealthy_pods(pods)

    console.print(f"Authentication: {authentication_source}")
    print_scan_summary(len(pods), len(unhealthy_pods), namespace)
    if not unhealthy_pods:
        console.print("[green]No pods with explicit failure signals were found.[/green]")
        return 0

    for pod in unhealthy_pods:
        evidence = collect_pod_evidence(core_api, apps_api, pod)
        rule_result = analyze_pod(evidence)
        ai_result = analyze_with_gemini(evidence, rule_result, model)
        print_diagnosis(evidence, rule_result, ai_result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Kubernetes pod troubleshooting.")
    parser.add_argument("command", choices=["scan", "check-connectivity"])
    parser.add_argument("--namespace", help="Limit the scan to one namespace.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model name for every scan.")
    return parser


def main() -> int:
    load_dotenv()
    arguments = build_parser().parse_args()
    try:
        if arguments.command == "check-connectivity":
            return check_connectivity(arguments.namespace)
        return scan(arguments.namespace, arguments.model)
    except GeminiConfigurationError as error:
        console.print(f"[red]Gemini configuration failed: {error}[/red]")
    except ConfigException as error:
        console.print(f"[red]Kubernetes authentication failed: {error}[/red]")
    except ApiException as error:
        console.print(f"[red]Kubernetes API error {error.status}: {error.reason}[/red]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
