"""Tests for Bugalizer integration — config, client, payload mapping, CLI."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qaagent.config.models import BugalizerSettings, QAAgentProfile, ProjectSettings
from qaagent.integrations.bugalizer_client import (
    SEVERITY_MAP,
    BugalizerClient,
    _build_bug_payload,
    _match_diagnostic,
    load_diagnostics,
    persist_diagnostics,
    submit_failures_to_bugalizer,
)
from qaagent.commands.run_cmd import _recompute_diagnostics_from_evidence
from qaagent.runners.base import TestCase, TestResult
from qaagent.runners.diagnostics import DiagnosticResult, RunDiagnosticSummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bugalizer_settings():
    return BugalizerSettings(
        enabled=True,
        api_url="http://localhost:8001",
        api_key_env="BUGALIZER_API_KEY",
        project_id="test-project",
        reporter="qaagent",
        labels=["qaagent", "ci"],
    )


@pytest.fixture
def failed_case():
    return TestCase(
        name="test_get_users_success",
        status="failed",
        duration=1.5,
        error_message="AssertionError: Expected 200 but got 500",
        route="GET /users",
    )


@pytest.fixture
def error_case():
    return TestCase(
        name="test_post_login",
        status="error",
        duration=0.3,
        error_message="ConnectionRefusedError: [Errno 61] Connection refused",
    )


@pytest.fixture
def diagnostic():
    return DiagnosticResult(
        root_cause="Server returned 500 instead of 200",
        category="assertion",
        suggestion="Check server error logs for internal failures.",
        confidence=0.8,
    )


@pytest.fixture
def suite_result(failed_case, error_case):
    return TestResult(
        suite_name="unit",
        runner="pytest",
        passed=3,
        failed=1,
        errors=1,
        duration=5.0,
        cases=[
            TestCase(name="test_health", status="passed", duration=0.1),
            TestCase(name="test_list_items", status="passed", duration=0.2),
            TestCase(name="test_create_item", status="passed", duration=0.3),
            failed_case,
            error_case,
        ],
    )


@pytest.fixture
def diagnostic_summary(diagnostic):
    return RunDiagnosticSummary(
        total_failures=2,
        categories={"assertion": 1, "connection": 1},
        diagnostics=[
            diagnostic,
            DiagnosticResult(
                root_cause="Connection refused",
                category="connection",
                suggestion="Verify the target service is running.",
                confidence=0.7,
            ),
        ],
        summary_text="2 failures: 1 assertion, 1 connection.",
    )


# ---------------------------------------------------------------------------
# Config Model Tests
# ---------------------------------------------------------------------------

class TestBugalizerSettings:
    def test_defaults(self):
        settings = BugalizerSettings()
        assert settings.enabled is False
        assert settings.api_url == "http://localhost:8001"
        assert settings.api_key_env == "BUGALIZER_API_KEY"
        assert settings.project_id is None
        assert settings.reporter == "qaagent"
        assert settings.labels == ["qaagent"]

    def test_custom_values(self):
        settings = BugalizerSettings(
            enabled=True,
            api_url="http://bugalizer.local:9000",
            project_id="my-project",
            labels=["team-a", "nightly"],
        )
        assert settings.enabled is True
        assert settings.api_url == "http://bugalizer.local:9000"
        assert settings.project_id == "my-project"
        assert settings.labels == ["team-a", "nightly"]

    def test_profile_includes_bugalizer(self):
        profile = QAAgentProfile(
            project=ProjectSettings(name="test"),
            bugalizer=BugalizerSettings(enabled=True, project_id="p1"),
        )
        assert profile.bugalizer is not None
        assert profile.bugalizer.enabled is True
        assert profile.bugalizer.project_id == "p1"

    def test_profile_bugalizer_none_by_default(self):
        profile = QAAgentProfile(project=ProjectSettings(name="test"))
        assert profile.bugalizer is None

    def test_serialization_roundtrip(self):
        settings = BugalizerSettings(enabled=True, project_id="p1")
        data = settings.model_dump()
        restored = BugalizerSettings(**data)
        assert restored == settings


# ---------------------------------------------------------------------------
# Payload Mapping Tests
# ---------------------------------------------------------------------------

class TestBuildBugPayload:
    def test_basic_payload(self, failed_case, diagnostic, suite_result, bugalizer_settings):
        payload = _build_bug_payload(failed_case, diagnostic, suite_result, bugalizer_settings)

        assert payload["title"] == "[pytest/assertion] test_get_users_success"
        assert "Root Cause: Server returned 500" in payload["description"]
        assert payload["reporter"] == "qaagent"
        assert payload["project_id"] == "test-project"
        assert payload["severity"] == "high"  # assertion -> high
        assert "qaagent" in payload["labels"]
        assert "unit" in payload["labels"]
        assert "pytest" in payload["labels"]
        assert payload["feature_area"] == "GET /users"
        assert len(payload["steps_to_reproduce"]) == 3

    def test_severity_mapping_all_categories(self):
        assert SEVERITY_MAP["auth"] == "critical"
        assert SEVERITY_MAP["assertion"] == "high"
        assert SEVERITY_MAP["connection"] == "high"
        assert SEVERITY_MAP["timeout"] == "medium"
        assert SEVERITY_MAP["data"] == "medium"
        assert SEVERITY_MAP["flaky"] == "low"
        assert SEVERITY_MAP["unknown"] == "medium"

    def test_no_route_omits_feature_area(self, diagnostic, suite_result, bugalizer_settings):
        case = TestCase(name="test_something", status="failed", error_message="fail")
        payload = _build_bug_payload(case, diagnostic, suite_result, bugalizer_settings)
        assert "feature_area" not in payload

    def test_long_title_truncated(self, diagnostic, suite_result, bugalizer_settings):
        case = TestCase(name="x" * 600, status="failed", error_message="fail")
        payload = _build_bug_payload(case, diagnostic, suite_result, bugalizer_settings)
        assert len(payload["title"]) <= 500


# ---------------------------------------------------------------------------
# Diagnostic Matching Tests
# ---------------------------------------------------------------------------

class TestMatchDiagnostic:
    def test_match_by_content(self):
        case = TestCase(
            name="test_login",
            status="failed",
            error_message="Connection refused",
        )
        summary = RunDiagnosticSummary(
            total_failures=1,
            diagnostics=[
                DiagnosticResult(
                    root_cause="Connection refused",
                    category="connection",
                    confidence=0.7,
                ),
            ],
        )
        diag = _match_diagnostic(case, summary)
        assert diag.category == "connection"
        assert diag.confidence == 0.7

    def test_fallback_when_no_summary(self, failed_case):
        diag = _match_diagnostic(failed_case, None)
        assert diag.category == "unknown"
        assert diag.confidence == 0.3
        assert diag.root_cause == failed_case.error_message

    def test_single_diagnostic_matches(self, failed_case):
        summary = RunDiagnosticSummary(
            total_failures=1,
            diagnostics=[DiagnosticResult(root_cause="some cause", category="timeout")],
        )
        diag = _match_diagnostic(failed_case, summary)
        assert diag.category == "timeout"


# ---------------------------------------------------------------------------
# Client Tests
# ---------------------------------------------------------------------------

class TestBugalizerClient:
    def test_submit_report_success(self, bugalizer_settings):
        client = BugalizerClient(bugalizer_settings)
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "bug-123", "title": "test bug", "status": "submitted"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.post.return_value = mock_response

        import httpx as httpx_mod
        with patch.object(httpx_mod, "Client", return_value=mock_http_client):
            result = client.submit_report({"title": "test", "description": "d", "reporter": "qa", "project_id": "p"})
            assert result["id"] == "bug-123"
            mock_http_client.post.assert_called_once()

    def test_submit_report_api_error(self, bugalizer_settings):
        client = BugalizerClient(bugalizer_settings)

        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.post.return_value.raise_for_status.side_effect = Exception("500 Server Error")

        import httpx as httpx_mod
        with patch.object(httpx_mod, "Client", return_value=mock_http_client):
            with pytest.raises(Exception, match="500 Server Error"):
                client.submit_report({"title": "test", "description": "d", "reporter": "qa", "project_id": "p"})

    def test_api_key_from_env(self, bugalizer_settings):
        with patch.dict("os.environ", {"BUGALIZER_API_KEY": "secret-key-123"}):
            client = BugalizerClient(bugalizer_settings)
            assert client._api_key == "secret-key-123"

    def test_api_key_empty_when_not_set(self, bugalizer_settings):
        with patch.dict("os.environ", {}, clear=True):
            client = BugalizerClient(bugalizer_settings)
            assert client._api_key == ""


# ---------------------------------------------------------------------------
# Submit Failures Tests
# ---------------------------------------------------------------------------

class TestSubmitFailures:
    def test_submit_failures_calls_client(self, bugalizer_settings, suite_result, diagnostic_summary):
        with patch("qaagent.integrations.bugalizer_client.BugalizerClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.submit_test_failure.return_value = {"id": "bug-1", "title": "t"}

            results = submit_failures_to_bugalizer(
                bugalizer_settings,
                {"unit": suite_result},
                diagnostic_summary,
            )

            # 2 failures in suite_result (failed + error)
            assert mock_instance.submit_test_failure.call_count == 2
            assert len(results) == 2

    def test_submit_failures_handles_errors_gracefully(self, bugalizer_settings, suite_result, diagnostic_summary):
        with patch("qaagent.integrations.bugalizer_client.BugalizerClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.submit_test_failure.side_effect = Exception("Connection refused")

            results = submit_failures_to_bugalizer(
                bugalizer_settings,
                {"unit": suite_result},
                diagnostic_summary,
            )

            # Should not raise, just return empty
            assert len(results) == 0

    def test_skips_passing_tests(self, bugalizer_settings):
        suite = TestResult(
            suite_name="unit",
            runner="pytest",
            passed=2,
            cases=[
                TestCase(name="test_a", status="passed"),
                TestCase(name="test_b", status="passed"),
            ],
        )

        with patch("qaagent.integrations.bugalizer_client.BugalizerClient") as MockClient:
            results = submit_failures_to_bugalizer(bugalizer_settings, {"unit": suite})
            MockClient.return_value.submit_test_failure.assert_not_called()
            assert len(results) == 0


# ---------------------------------------------------------------------------
# Diagnostic Persistence Tests
# ---------------------------------------------------------------------------

class TestDiagnosticPersistence:
    def test_persist_and_load(self, tmp_path, suite_result, diagnostic_summary):
        diag_path = persist_diagnostics(tmp_path, {"unit": suite_result}, diagnostic_summary)

        assert diag_path.exists()
        assert diag_path.name == "diagnostics.json"

        records = load_diagnostics(tmp_path)
        assert len(records) == 2  # 2 failures

        assert records[0]["test_name"] == "test_get_users_success"
        assert records[0]["suite"] == "unit"
        assert records[0]["category"] == "assertion"
        assert records[0]["confidence"] == 0.8

        assert records[1]["test_name"] == "test_post_login"
        assert records[1]["category"] == "connection"

    def test_load_missing_returns_empty(self, tmp_path):
        records = load_diagnostics(tmp_path)
        assert records == []

    def test_persist_with_routes(self, tmp_path, diagnostic_summary):
        suite = TestResult(
            suite_name="unit",
            runner="pytest",
            failed=1,
            cases=[
                TestCase(
                    name="test_get_users",
                    status="failed",
                    error_message="500",
                    route="GET /users",
                ),
            ],
        )
        persist_diagnostics(tmp_path, {"unit": suite}, diagnostic_summary)
        records = load_diagnostics(tmp_path)
        assert records[0]["route"] == "GET /users"


# ---------------------------------------------------------------------------
# Legacy Run Recompute Fallback Tests
# ---------------------------------------------------------------------------

JUNIT_FAILURE_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuite name="unit" tests="3" failures="1" errors="1">
  <testcase classname="tests.test_api" name="test_health" time="0.1"/>
  <testcase classname="tests.test_api" name="test_get_users" time="1.2">
    <failure message="AssertionError: Expected 200 but got 500">Traceback ...</failure>
  </testcase>
  <testcase classname="tests.test_api" name="test_login" time="0.3">
    <error message="ConnectionRefusedError: Connection refused">Traceback ...</error>
  </testcase>
</testsuite>
"""

JUNIT_ALL_PASS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuite name="smoke" tests="2" failures="0">
  <testcase classname="tests.test_smoke" name="test_a" time="0.1"/>
  <testcase classname="tests.test_smoke" name="test_b" time="0.2"/>
</testsuite>
"""


class TestRecomputeDiagnosticsFromEvidence:
    def _make_handle(self, tmp_path):
        """Create a minimal mock handle with artifacts_dir."""
        handle = MagicMock()
        handle.artifacts_dir = tmp_path / "artifacts"
        handle.artifacts_dir.mkdir(parents=True)
        handle.evidence_dir = tmp_path / "evidence"
        handle.evidence_dir.mkdir(parents=True)
        return handle

    def _make_profile(self):
        """Create a minimal profile with LLM disabled."""
        profile = MagicMock()
        profile.llm = MagicMock()
        profile.llm.enabled = False
        return profile

    def test_recompute_finds_failures(self, tmp_path):
        handle = self._make_handle(tmp_path)
        profile = self._make_profile()

        # Create JUnit XML in artifacts/unit/junit/pytest-junit.xml
        junit_dir = handle.artifacts_dir / "unit" / "junit"
        junit_dir.mkdir(parents=True)
        (junit_dir / "pytest-junit.xml").write_text(JUNIT_FAILURE_XML)

        records = _recompute_diagnostics_from_evidence(handle, profile)

        assert len(records) == 2
        assert records[0]["test_name"] == "test_get_users"
        assert records[0]["suite"] == "unit"
        assert records[0]["category"] == "assertion"
        assert records[0]["error_message"] == "AssertionError: Expected 200 but got 500"

        assert records[1]["test_name"] == "test_login"
        assert records[1]["suite"] == "unit"
        assert records[1]["category"] == "connection"

    def test_recompute_all_passing_returns_empty(self, tmp_path):
        handle = self._make_handle(tmp_path)
        profile = self._make_profile()

        junit_dir = handle.artifacts_dir / "smoke" / "junit"
        junit_dir.mkdir(parents=True)
        (junit_dir / "results.xml").write_text(JUNIT_ALL_PASS_XML)

        records = _recompute_diagnostics_from_evidence(handle, profile)
        assert records == []

    def test_recompute_no_artifacts_dir(self, tmp_path):
        handle = MagicMock()
        handle.artifacts_dir = tmp_path / "nonexistent"
        profile = self._make_profile()

        records = _recompute_diagnostics_from_evidence(handle, profile)
        assert records == []

    def test_recompute_multiple_suites(self, tmp_path):
        handle = self._make_handle(tmp_path)
        profile = self._make_profile()

        # Suite 1: unit with failures
        unit_dir = handle.artifacts_dir / "unit" / "junit"
        unit_dir.mkdir(parents=True)
        (unit_dir / "pytest-junit.xml").write_text(JUNIT_FAILURE_XML)

        # Suite 2: e2e with all passing
        e2e_dir = handle.artifacts_dir / "e2e" / "junit"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "playwright-junit.xml").write_text(JUNIT_ALL_PASS_XML)

        records = _recompute_diagnostics_from_evidence(handle, profile)

        # Only failures from unit suite
        assert len(records) == 2
        assert all(r["suite"] == "unit" for r in records)

    def test_recompute_records_have_expected_keys(self, tmp_path):
        handle = self._make_handle(tmp_path)
        profile = self._make_profile()

        junit_dir = handle.artifacts_dir / "unit" / "junit"
        junit_dir.mkdir(parents=True)
        (junit_dir / "pytest-junit.xml").write_text(JUNIT_FAILURE_XML)

        records = _recompute_diagnostics_from_evidence(handle, profile)

        expected_keys = {
            "test_name", "suite", "category", "root_cause",
            "confidence", "suggestion", "error_message", "route",
        }
        for record in records:
            assert set(record.keys()) == expected_keys
