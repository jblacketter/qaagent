"""LLM client for qaagent — multi-provider via litellm.

LLMClient is the ONLY place that imports litellm. All qaagent code should use
LLMClient or the module-level convenience functions (chat, llm_available, etc.).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from .openapi_utils import enumerate_operations


class ChatMessage(BaseModel):
    """A chat message with role and content."""
    role: str  # "system" | "user" | "assistant"
    content: str


class ChatResponse(BaseModel):
    """Response from an LLM chat completion."""
    content: str
    model: str = ""
    usage: Optional[Dict[str, Any]] = None


class QAAgentLLMError(Exception):
    """Raised when the LLM client encounters an error."""
    pass


class LLMClient:
    """Thin wrapper around litellm with qaagent defaults.

    Provider selection uses litellm model string format:
    - "ollama/qwen2.5:7b" for local Ollama
    - "anthropic/claude-sonnet-4-5-20250929" for Anthropic
    - "gpt-4o" for OpenAI
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        self.provider = provider or os.environ.get("QAAGENT_LLM", "ollama")
        self.model = model or os.environ.get("QAAGENT_MODEL", "qwen2.5:7b")
        self.temperature = temperature or float(os.environ.get("QAAGENT_TEMP", "0.2"))

    def _litellm_model(self) -> str:
        """Build the litellm model string from provider + model."""
        if self.provider == "ollama":
            return f"ollama/{self.model}"
        if self.provider == "anthropic":
            return f"anthropic/{self.model}"
        if self.provider in ("openai", "gpt"):
            return self.model  # OpenAI models don't need prefix
        # Default: pass through as-is (litellm can figure it out)
        return f"{self.provider}/{self.model}" if "/" not in self.model else self.model

    def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send messages to configured LLM provider via litellm."""
        try:
            import litellm
        except ImportError as exc:
            raise QAAgentLLMError(
                "litellm is not installed. Install LLM extras: pip install -e .[llm]"
            ) from exc

        litellm_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            response = litellm.completion(
                model=self._litellm_model(),
                messages=litellm_messages,
                temperature=self.temperature,
            )
        except Exception as exc:
            raise QAAgentLLMError(f"LLM request failed: {exc}") from exc

        content = response.choices[0].message.content or ""
        usage_data = None
        if hasattr(response, "usage") and response.usage:
            usage_data = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                "completion_tokens": getattr(response.usage, "completion_tokens", None),
                "total_tokens": getattr(response.usage, "total_tokens", None),
            }

        return ChatResponse(
            content=content,
            model=getattr(response, "model", self._litellm_model()),
            usage=usage_data,
        )

    def available(self) -> bool:
        """Check if the configured provider is reachable."""
        try:
            import litellm  # noqa: F401
        except ImportError:
            return False

        if self.provider == "ollama":
            try:
                import ollama  # type: ignore
                ollama.list()
                return True
            except Exception:
                return False

        # For cloud providers, just check that the SDK is importable
        if self.provider == "anthropic":
            try:
                import anthropic  # type: ignore  # noqa: F401
                return bool(os.environ.get("ANTHROPIC_API_KEY"))
            except ImportError:
                return False

        if self.provider in ("openai", "gpt"):
            try:
                import openai  # type: ignore  # noqa: F401
                return bool(os.environ.get("OPENAI_API_KEY"))
            except ImportError:
                return False

        return True


# ---------------------------------------------------------------------------
# Module-level singleton and convenience functions (backward compat)
# ---------------------------------------------------------------------------

_default_client: Optional[LLMClient] = None


def _get_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def llm_available() -> bool:
    """Check if an LLM provider is available."""
    return _get_client().available()


def chat(
    messages: List[Dict[str, str]],
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Backward-compat chat function. Returns a dict like the old Ollama API."""
    client = _get_client()
    typed_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
    response = client.chat(typed_messages)
    # Return in the old Ollama response format for backward compat
    return {
        "message": {"role": "assistant", "content": response.content},
        "model": response.model,
    }


def generate_api_tests_from_spec(
    spec: Dict[str, Any],
    base_url: Optional[str] = None,
    operations: Optional[List[Tuple[str, str]]] = None,
    max_tests: int = 12,
    retrieval_context: Optional[List[str]] = None,
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
        if retrieval_context:
            lines += [
                "# Retrieval context used to guide generation:",
                *[f"# - {snippet.splitlines()[0][:120]}" for snippet in retrieval_context[:5]],
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
    rag_text = ""
    if retrieval_context:
        rag_sections = []
        for idx, snippet in enumerate(retrieval_context[:8], start=1):
            rag_sections.append(f"[Context {idx}]\n{snippet[:2000]}")
        rag_text = "\n\nRepository context snippets:\n" + "\n\n".join(rag_sections)
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"Base URL: {base_url or 'http://localhost:8000'}\n"
                f"Operations:\n{ops_text}"
                f"{rag_text}"
            ),
        },
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
