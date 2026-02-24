"""Bugalizer integration client.

Submits structured bug reports to Bugalizer's REST API from QA Agent
test failures and diagnostic results.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from qaagent.config.models import BugalizerSettings
from qaagent.runners.base import TestCase, TestResult
from qaagent.runners.diagnostics import DiagnosticResult, RunDiagnosticSummary

logger = logging.getLogger(__name__)

# Map diagnostic categories to Bugalizer severity levels
SEVERITY_MAP: Dict[str, str] = {
    "auth": "critical",
    "assertion": "high",
    "connection": "high",
    "timeout": "medium",
    "data": "medium",
    "flaky": "low",
    "unknown": "medium",
}


def _build_bug_payload(
    case: TestCase,
    diagnostic: DiagnosticResult,
    suite_result: TestResult,
    settings: BugalizerSettings,
) -> Dict[str, Any]:
    """Convert a failed TestCase + DiagnosticResult into a Bugalizer report payload."""
    title = f"[{suite_result.runner}/{diagnostic.category}] {case.name}"
    if len(title) > 500:
        title = title[:497] + "..."

    description = (
        f"Test Suite: {suite_result.suite_name} ({suite_result.runner})\n"
        f"Test Case: {case.name}\n\n"
        f"Root Cause: {diagnostic.root_cause}\n"
        f"Category: {diagnostic.category}\n"
        f"Confidence: {diagnostic.confidence:.0%}\n\n"
        f"Error Message:\n{case.error_message or 'N/A'}\n\n"
        f"Suggestion:\n{diagnostic.suggestion}"
    )

    steps = [
        f"Run suite '{suite_result.suite_name}' with runner '{suite_result.runner}'",
        f"Execute test '{case.name}'",
        "Observe failure matching error message above",
    ]

    severity = SEVERITY_MAP.get(diagnostic.category, "medium")

    labels = list(settings.labels) + [suite_result.suite_name, suite_result.runner]

    payload: Dict[str, Any] = {
        "title": title,
        "description": description,
        "reporter": settings.reporter,
        "project_id": settings.project_id or "default",
        "steps_to_reproduce": steps,
        "expected_behavior": f"Test '{case.name}' passes",
        "actual_behavior": f"Test {case.status}: {(case.error_message or 'Unknown')[:200]}",
        "severity": severity,
        "labels": labels,
    }

    if case.route:
        payload["feature_area"] = case.route

    return payload


def _match_diagnostic(
    case: TestCase,
    diagnostic_summary: Optional[RunDiagnosticSummary],
) -> DiagnosticResult:
    """Find the matching DiagnosticResult for a failed test case.

    Falls back to a minimal diagnostic if no match found.
    """
    if diagnostic_summary:
        # Diagnostics are produced in the same order as failures were collected
        # Try matching by root_cause content
        for diag in diagnostic_summary.diagnostics:
            if case.error_message and case.error_message in diag.root_cause:
                return diag
            if diag.root_cause and diag.root_cause in (case.error_message or ""):
                return diag

        # If only one diagnostic and one failure, they match
        if len(diagnostic_summary.diagnostics) == 1:
            return diagnostic_summary.diagnostics[0]

    return DiagnosticResult(
        root_cause=case.error_message or "Unknown error",
        category="unknown",
        suggestion="Review the full error output for more context.",
        confidence=0.3,
    )


class BugalizerClient:
    """HTTP client for submitting bug reports to Bugalizer."""

    def __init__(self, settings: BugalizerSettings) -> None:
        self.settings = settings
        self.api_url = settings.api_url.rstrip("/")
        self._api_key = os.environ.get(settings.api_key_env, "")

    def submit_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a bug report to Bugalizer. Returns the response data."""
        import httpx

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key

        url = f"{self.api_url}/api/v1/reports"
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def submit_test_failure(
        self,
        case: TestCase,
        diagnostic: DiagnosticResult,
        suite_result: TestResult,
    ) -> Dict[str, Any]:
        """Build payload from test failure and submit to Bugalizer."""
        payload = _build_bug_payload(case, diagnostic, suite_result, self.settings)
        return self.submit_report(payload)


def submit_failures_to_bugalizer(
    settings: BugalizerSettings,
    suites: Dict[str, TestResult],
    diagnostic_summary: Optional[RunDiagnosticSummary] = None,
) -> List[Dict[str, Any]]:
    """Submit all failed test cases as bug reports to Bugalizer.

    Returns list of submitted report responses.
    """
    client = BugalizerClient(settings)
    submitted: List[Dict[str, Any]] = []

    for suite_name, suite_result in suites.items():
        for case in suite_result.cases:
            if case.status not in ("failed", "error"):
                continue

            diagnostic = _match_diagnostic(case, diagnostic_summary)

            try:
                result = client.submit_test_failure(case, diagnostic, suite_result)
                submitted.append(result)
                logger.info(
                    "Submitted bug report: %s - %s",
                    result.get("id", "?"),
                    result.get("title", case.name),
                )
            except Exception:
                logger.warning(
                    "Failed to submit bug for test '%s'",
                    case.name,
                    exc_info=True,
                )

    return submitted


def persist_diagnostics(
    evidence_dir: Path,
    suites: Dict[str, TestResult],
    diagnostic_summary: RunDiagnosticSummary,
) -> Path:
    """Write per-test diagnostic records to diagnostics.json in evidence."""
    # Collect failed cases in the same order diagnostics were produced
    failed_cases: List[TestCase] = []
    failed_suites: List[str] = []
    for suite_name, suite_result in suites.items():
        for case in suite_result.cases:
            if case.status in ("failed", "error"):
                failed_cases.append(case)
                failed_suites.append(suite_name)

    records = []
    for i, (case, suite_name) in enumerate(zip(failed_cases, failed_suites)):
        diag = (
            diagnostic_summary.diagnostics[i]
            if i < len(diagnostic_summary.diagnostics)
            else DiagnosticResult(root_cause=case.error_message or "Unknown")
        )
        records.append({
            "test_name": case.name,
            "suite": suite_name,
            "category": diag.category,
            "root_cause": diag.root_cause,
            "confidence": diag.confidence,
            "suggestion": diag.suggestion,
            "error_message": case.error_message,
            "route": case.route,
        })

    diagnostics_path = evidence_dir / "diagnostics.json"
    diagnostics_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return diagnostics_path


def load_diagnostics(evidence_dir: Path) -> List[Dict[str, Any]]:
    """Load persisted diagnostics from a run's evidence directory."""
    diagnostics_path = evidence_dir / "diagnostics.json"
    if not diagnostics_path.exists():
        return []
    return json.loads(diagnostics_path.read_text(encoding="utf-8"))
