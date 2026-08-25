"""Optional Gemini analysis that augments deterministic Kubernetes rules."""

from __future__ import annotations

import json
import os

from google import genai

from .models import AiResult, PodEvidence, RuleResult

DEFAULT_MODEL = "gemini-3.7-flash"


def analyze_with_gemini(
    pod: PodEvidence, rule_result: RuleResult, model: str = DEFAULT_MODEL
) -> AiResult:
    """Request evidence-bounded advice from Gemini when explicitly enabled."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return AiResult(error="GEMINI_API_KEY is not set; deterministic diagnosis is shown instead.")

    prompt = f"""You are assisting a Kubernetes operator. Use only the evidence provided.
Do not invent resource names, events, log lines, configuration values, or causes.
If the evidence is insufficient, say exactly what additional information is needed.

Return concise Markdown with these headings:
Detected problem; Most likely root cause; Evidence; Investigation steps;
Useful kubectl commands; Recommended remediation; Confidence.

Deterministic rule result:
{json.dumps(rule_result.__dict__, indent=2)}

Collected pod evidence:
{json.dumps(pod.to_dict(), indent=2)}
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as error:  # API failures must not hide deterministic results.
        return AiResult(error=f"Gemini request failed: {error}")

    if not response.text:
        return AiResult(error="Gemini returned no text response.")
    return AiResult(text=response.text)
