"""Terminal rendering for Kubernetes evidence and Gemini diagnoses."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import AiResult, PodEvidence, RuleResult

console = Console()


def print_scan_summary(scanned: int, unhealthy: int, namespace: str | None) -> None:
    scope = namespace or "all namespaces"
    console.print("[bold]Kubernetes AI Troubleshooter[/bold]")
    console.print(f"Scanning: {scope}")
    console.print(f"Pods scanned: {scanned}; unhealthy pods found: {unhealthy}\n")


def print_diagnosis(pod: PodEvidence, rule: RuleResult, ai_result: AiResult | None) -> None:
    header = f"{pod.namespace}/{pod.name} — {pod.phase}"
    console.print(Panel(f"[bold red]{rule.category}[/bold red]\n{rule.summary}", title=header))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Container")
    table.add_column("State")
    table.add_column("Ready")
    table.add_column("Restarts", justify="right")
    for container in pod.containers:
        detail = container.waiting_reason or container.termination_reason or container.state
        table.add_row(container.name, detail, str(container.ready), str(container.restart_count))
    console.print(table)

    console.print("[bold]Evidence[/bold]")
    for item in rule.evidence:
        console.print(f"- {item}")
    if ai_result and ai_result.text:
        console.print(Panel(ai_result.text, title="Gemini analysis"))
    elif ai_result and ai_result.error:
        console.print(f"[yellow]Gemini analysis failed: {ai_result.error}[/yellow]")
    console.print()
