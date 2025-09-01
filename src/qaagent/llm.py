from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .openapi_utils import enumerate_operations


def _import_ollama():
    try:
        import ollama  # type: ignore

        return ollama
    except Exception:
        return None


@dataclass
class LLMConfig:
    provider: str = os.environ.get("QAAGENT_LLM", "ollama")
    model: str = os.environ.get("QAAGENT_MODEL", "qwen2.5:7b")
    temperature: float = float(os.environ.get("QAAGENT_TEMP", 0.2))


def llm_available() -> bool:
    cfg = LLMConfig()
    if cfg.provider == "ollama":
        return _import_ollama() is not None
    # Other providers could be added later
    return False


def chat(messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    cfg = LLMConfig()
    if cfg.provider == "ollama":
        ollama = _import_ollama()
        if not ollama:
            raise RuntimeError("Ollama is not installed. Install extras: pip install -e .[llm]")
        # Use the simple chat API
        return ollama.chat(
            model=cfg.model,
            messages=messages,
            options={"temperature": cfg.temperature},
            tools=tools or None,
        )
    raise RuntimeError(f"Unsupported LLM provider: {cfg.provider}")


def generate_api_tests_from_spec(
    spec: Dict[str, Any],
    base_url: Optional[str] = None,
    operations: Optional[List[Tuple[str, str]]] = None,
    max_tests: int = 12,
) -> str:
    """Generate pytest + httpx tests for selected operations.

    Falls back to deterministic template generation if LLM is not available.
    """
    ops = enumerate_operations(spec)
    selected: List[Tuple[str, str, Optional[str]]] = []
    for op in ops[: max_tests * 2]:
        if operations and (op.method, op.path) not in operations:
            continue
        selected.append((op.method, op.path, op.operation_id))
        if len(selected) >= max_tests:
            break

    if not llm_available():
        # Deterministic fallback: simple status < 500 checks
        lines = [
            "import os",
            "import httpx",
            "import pytest",
            "",
            "BASE_URL = os.environ.get('BASE_URL', '%s')" % (base_url or "http://localhost:8000"),
            "",
        ]
        for i, (method, path, op_id) in enumerate(selected, start=1):
            test_name = op_id or f"{method.lower()}_{path.strip('/').replace('/', '_').replace('{','').replace('}','')}"
            if not test_name:
                test_name = f"endpoint_{i}"
            lines += [
                f"def test_{test_name}():",
                f"    url = BASE_URL + '{path}'",
                f"    with httpx.Client(timeout=10.0) as client:",
                f"        resp = client.request('{method}', url)",
                f"    assert resp.status_code < 500",
                "",
            ]
        return "\n".join(lines) + "\n"

    # LLM-based generation
    prompt = (
        "You are a QA engineer. Generate concise pytest tests using httpx for the given OpenAPI operations. "
        "Keep tests deterministic and do not require auth unless specified. Use BASE_URL env var if available. "
        "For each operation, create a test that calls the endpoint with reasonable defaults and asserts status code < 500. "
        "Return only Python code."
    )
    ops_text = "\n".join([f"- {m} {p} (operationId={op or '-'})" for m, p, op in selected])
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Base URL: {base_url or 'http://localhost:8000'}\nOperations:\n{ops_text}"},
    ]
    resp = chat(messages)
    content = resp.get("message", {}).get("content") if isinstance(resp, dict) else None
    if not content:
        raise RuntimeError("LLM did not return content")
    return content.strip() + ("\n" if not content.endswith("\n") else "")


def summarize_findings_text(summary: Dict[str, Any]) -> str:
    """Produce an executive summary string from report metadata.

    If LLM is available, ask it to refine the summary for stakeholders; otherwise, return a templated version.
    """
    base = _templated_summary(summary)
    if not llm_available():
        return base
    messages = [
        {"role": "system", "content": "You are a senior QA consultant. Write a crisp executive summary (6-10 bullets)."},
        {"role": "user", "content": base},
    ]
    try:
        resp = chat(messages)
        content = resp.get("message", {}).get("content")
        return content.strip() if content else base
    except Exception:
        return base


def _templated_summary(summary: Dict[str, Any]) -> str:
    parts = ["# QA Executive Summary", ""]
    totals = summary.get("summary", {})
    parts.append(
        f"- Tests: {totals.get('tests', 0)} | Failures: {totals.get('failures', 0)} | Errors: {totals.get('errors', 0)} | Skipped: {totals.get('skipped', 0)}"
    )
    extras = summary.get("extras", {}) or {}
    if extras.get("api_coverage"):
        cov = extras["api_coverage"]
        parts.append(
            f"- API coverage: {cov.get('covered', 0)}/{cov.get('total', 0)} operations ({cov.get('pct', 0)}%)"
        )
    if extras.get("a11y"):
        parts.append(f"- Accessibility violations: {extras['a11y'].get('violations', 0)} (axe)")
    if extras.get("lighthouse") and extras["lighthouse"].get("scores"):
        sc = extras["lighthouse"]["scores"]
        perf = sc.get("performance")
        if perf is not None:
            parts.append(f"- Lighthouse performance score: {perf}")
    if extras.get("perf"):
        pf = extras["perf"]
        rps = pf.get("rps")
        p95 = pf.get("p95_response_time")
        if rps or p95:
            parts.append(f"- Perf: RPS={rps} | p95={p95}")
    parts += [
        "- Top risks: stabilize UI selectors; expand negative cases; add auth scenarios",
        "- Next steps: increase API coverage; add regression suite; integrate CI gating",
    ]
    return "\n".join(parts) + "\n"

