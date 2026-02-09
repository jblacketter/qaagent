"""LLM-powered failure diagnostics for test results.

Analyzes test failures, categorizes root causes, and suggests fixes.
Falls back to structured error summaries when LLM is unavailable.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from pydantic import BaseModel, Field

from qaagent.config.models import LLMSettings
from qaagent.runners.base import TestCase, TestResult

logger = logging.getLogger(__name__)

# Failure categories
CATEGORY_ASSERTION = "assertion"
CATEGORY_TIMEOUT = "timeout"
CATEGORY_CONNECTION = "connection"
CATEGORY_AUTH = "auth"
CATEGORY_DATA = "data"
CATEGORY_FLAKY = "flaky"
CATEGORY_UNKNOWN = "unknown"


class DiagnosticResult(BaseModel):
    """Analysis of a single test failure."""
    root_cause: str
    category: str = CATEGORY_UNKNOWN
    suggestion: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    fix_code: Optional[str] = None


class RunDiagnosticSummary(BaseModel):
    """Summary diagnostics for an entire orchestrator run."""
    total_failures: int = 0
    categories: dict[str, int] = Field(default_factory=dict)
    diagnostics: list[DiagnosticResult] = Field(default_factory=list)
    summary_text: str = ""


# Patterns for heuristic classification
_PATTERNS = [
    (CATEGORY_TIMEOUT, re.compile(r"timeout|timed?\s*out|TimeoutError|deadline exceeded", re.I)),
    (CATEGORY_CONNECTION, re.compile(r"connection\s*(refused|reset|error)|ECONNREFUSED|socket|network", re.I)),
    (CATEGORY_AUTH, re.compile(r"401|403|unauthorized|forbidden|authentication|permission denied", re.I)),
    (CATEGORY_DATA, re.compile(r"404|not found|null|undefined|missing.*field|KeyError", re.I)),
    (CATEGORY_FLAKY, re.compile(r"flaky|intermittent|race condition|stale element", re.I)),
    (CATEGORY_ASSERTION, re.compile(r"assert(ion)?|AssertionError|Expected.*but got|not equal", re.I)),
]


class FailureDiagnostics:
    """Analyze test failures and produce actionable diagnostics."""

    def __init__(self, llm_settings: Optional[LLMSettings] = None) -> None:
        self.llm_settings = llm_settings or LLMSettings()
        self._llm_client = None

    def _get_llm(self):
        """Lazy-init the LLM client."""
        if self._llm_client is None and self.llm_settings.enabled:
            try:
                from qaagent.llm import LLMClient
                client = LLMClient(
                    provider=self.llm_settings.provider,
                    model=self.llm_settings.model,
                )
                if client.available():
                    self._llm_client = client
            except Exception:
                logger.debug("LLM client not available for diagnostics")
        return self._llm_client

    def analyze_failure(
        self,
        case: TestCase,
        test_code: Optional[str] = None,
    ) -> DiagnosticResult:
        """Analyze a single test failure.

        Uses LLM if available, otherwise falls back to heuristic pattern matching.
        """
        llm = self._get_llm()
        if llm is not None:
            return self._analyze_with_llm(case, test_code, llm)
        return self._analyze_heuristic(case)

    def summarize_run(self, suites: dict[str, TestResult]) -> RunDiagnosticSummary:
        """Produce a diagnostic summary for an entire test run."""
        all_failures: List[TestCase] = []
        for suite_result in suites.values():
            for tc in suite_result.cases:
                if tc.status in ("failed", "error"):
                    all_failures.append(tc)

        if not all_failures:
            return RunDiagnosticSummary(
                summary_text="All tests passed. No failures to diagnose.",
            )

        diagnostics = [self.analyze_failure(tc) for tc in all_failures]

        categories: dict[str, int] = {}
        for d in diagnostics:
            categories[d.category] = categories.get(d.category, 0) + 1

        # Build summary text
        llm = self._get_llm()
        if llm is not None:
            summary_text = self._summarize_with_llm(all_failures, diagnostics, llm)
        else:
            summary_text = self._summarize_heuristic(all_failures, diagnostics, categories)

        return RunDiagnosticSummary(
            total_failures=len(all_failures),
            categories=categories,
            diagnostics=diagnostics,
            summary_text=summary_text,
        )

    def _analyze_heuristic(self, case: TestCase) -> DiagnosticResult:
        """Classify failure using regex patterns."""
        text = f"{case.error_message or ''} {case.output or ''}"
        category = CATEGORY_UNKNOWN

        for cat, pattern in _PATTERNS:
            if pattern.search(text):
                category = cat
                break

        suggestions = {
            CATEGORY_ASSERTION: "Check expected values against actual API response or UI state.",
            CATEGORY_TIMEOUT: "Increase timeout or check if the target service is running.",
            CATEGORY_CONNECTION: "Verify the target service is running and accessible.",
            CATEGORY_AUTH: "Check authentication credentials and token configuration.",
            CATEGORY_DATA: "Verify test data exists and API endpoints return expected resources.",
            CATEGORY_FLAKY: "Consider adding retries or stabilizing test preconditions.",
            CATEGORY_UNKNOWN: "Review the full error output for more context.",
        }

        return DiagnosticResult(
            root_cause=case.error_message or "Unknown error",
            category=category,
            suggestion=suggestions.get(category, suggestions[CATEGORY_UNKNOWN]),
            confidence=0.6 if category != CATEGORY_UNKNOWN else 0.3,
        )

    def _analyze_with_llm(
        self,
        case: TestCase,
        test_code: Optional[str],
        llm,
    ) -> DiagnosticResult:
        """Use LLM to analyze a test failure."""
        from qaagent.llm import ChatMessage

        prompt = (
            "Analyze this test failure and provide:\n"
            "1. Root cause (one sentence)\n"
            "2. Category (one of: assertion, timeout, connection, auth, data, flaky, unknown)\n"
            "3. Suggested fix (one sentence)\n"
            "4. Confidence (0.0-1.0)\n\n"
            f"Test: {case.name}\n"
            f"Status: {case.status}\n"
            f"Error: {case.error_message or 'N/A'}\n"
            f"Output: {(case.output or 'N/A')[:500]}\n"
        )
        if test_code:
            prompt += f"\nTest code:\n{test_code[:1000]}\n"

        prompt += (
            "\nRespond in this exact format:\n"
            "ROOT_CAUSE: <cause>\n"
            "CATEGORY: <category>\n"
            "SUGGESTION: <fix>\n"
            "CONFIDENCE: <number>\n"
        )

        try:
            response = llm.chat([
                ChatMessage(role="system", content="You are a QA engineer analyzing test failures."),
                ChatMessage(role="user", content=prompt),
            ])
            return self._parse_llm_diagnostic(response.content, case)
        except Exception:
            logger.debug("LLM diagnostic failed, falling back to heuristic")
            return self._analyze_heuristic(case)

    def _parse_llm_diagnostic(self, response: str, case: TestCase) -> DiagnosticResult:
        """Parse structured LLM response into DiagnosticResult."""
        lines = response.strip().split("\n")
        parsed = {}
        for line in lines:
            for key in ("ROOT_CAUSE", "CATEGORY", "SUGGESTION", "CONFIDENCE"):
                if line.upper().startswith(key + ":"):
                    parsed[key] = line.split(":", 1)[1].strip()

        valid_categories = {
            CATEGORY_ASSERTION, CATEGORY_TIMEOUT, CATEGORY_CONNECTION,
            CATEGORY_AUTH, CATEGORY_DATA, CATEGORY_FLAKY, CATEGORY_UNKNOWN,
        }
        category = parsed.get("CATEGORY", "").lower()
        if category not in valid_categories:
            category = CATEGORY_UNKNOWN

        try:
            confidence = float(parsed.get("CONFIDENCE", "0.5"))
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            confidence = 0.5

        return DiagnosticResult(
            root_cause=parsed.get("ROOT_CAUSE", case.error_message or "Unknown error"),
            category=category,
            suggestion=parsed.get("SUGGESTION", "Review the full error output."),
            confidence=confidence,
        )

    def _summarize_with_llm(
        self,
        failures: List[TestCase],
        diagnostics: List[DiagnosticResult],
        llm,
    ) -> str:
        """Generate an LLM-powered run summary."""
        from qaagent.llm import ChatMessage

        failure_lines = []
        for tc, diag in zip(failures, diagnostics):
            failure_lines.append(
                f"- {tc.name}: [{diag.category}] {diag.root_cause}"
            )
        failures_text = "\n".join(failure_lines[:20])  # Cap at 20

        prompt = (
            "Summarize these test failures in 2-3 sentences. "
            "Focus on common patterns and actionable recommendations.\n\n"
            f"Failures:\n{failures_text}\n"
        )

        try:
            response = llm.chat([
                ChatMessage(role="system", content="You are a QA engineer writing a test run summary."),
                ChatMessage(role="user", content=prompt),
            ])
            return response.content.strip()
        except Exception:
            return self._summarize_heuristic(failures, diagnostics, {})

    def _summarize_heuristic(
        self,
        failures: List[TestCase],
        diagnostics: List[DiagnosticResult],
        categories: dict[str, int],
    ) -> str:
        """Build a structured summary without LLM."""
        parts = [f"{len(failures)} test failure(s) detected."]

        if categories:
            cat_parts = [f"{count} {cat}" for cat, count in sorted(categories.items(), key=lambda x: -x[1])]
            parts.append(f"Breakdown: {', '.join(cat_parts)}.")

        # Top suggestions
        seen = set()
        suggestions = []
        for d in diagnostics:
            if d.suggestion and d.suggestion not in seen:
                seen.add(d.suggestion)
                suggestions.append(d.suggestion)
        if suggestions:
            parts.append("Suggestions: " + " ".join(suggestions[:3]))

        return " ".join(parts)
