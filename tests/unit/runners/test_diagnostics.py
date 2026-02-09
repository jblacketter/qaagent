"""Tests for FailureDiagnostics."""
from unittest.mock import MagicMock, patch

from qaagent.config.models import LLMSettings
from qaagent.runners.base import TestCase, TestResult
from qaagent.runners.diagnostics import (
    CATEGORY_ASSERTION,
    CATEGORY_AUTH,
    CATEGORY_CONNECTION,
    CATEGORY_DATA,
    CATEGORY_TIMEOUT,
    CATEGORY_UNKNOWN,
    DiagnosticResult,
    FailureDiagnostics,
    RunDiagnosticSummary,
)


class TestDiagnosticResult:
    def test_default_values(self):
        d = DiagnosticResult(root_cause="test error")
        assert d.category == CATEGORY_UNKNOWN
        assert d.confidence == 0.5

    def test_custom_values(self):
        d = DiagnosticResult(
            root_cause="assertion mismatch",
            category=CATEGORY_ASSERTION,
            suggestion="fix expected value",
            confidence=0.9,
        )
        assert d.category == CATEGORY_ASSERTION
        assert d.confidence == 0.9


class TestHeuristicDiagnostics:
    def setup_method(self):
        self.diag = FailureDiagnostics(LLMSettings(enabled=False))

    def test_assertion_error(self):
        case = TestCase(
            name="test_example",
            status="failed",
            error_message="AssertionError: expected 'hello' but got 'world'",
        )
        result = self.diag.analyze_failure(case)
        assert result.category == CATEGORY_ASSERTION
        assert result.confidence > 0.3

    def test_timeout_error(self):
        case = TestCase(
            name="test_slow",
            status="error",
            error_message="TimeoutError: operation timed out after 30s",
        )
        result = self.diag.analyze_failure(case)
        assert result.category == CATEGORY_TIMEOUT

    def test_connection_error(self):
        case = TestCase(
            name="test_api",
            status="error",
            error_message="ConnectionRefusedError: connection refused",
        )
        result = self.diag.analyze_failure(case)
        assert result.category == CATEGORY_CONNECTION

    def test_auth_error(self):
        case = TestCase(
            name="test_protected",
            status="failed",
            error_message="HTTP 401 Unauthorized: access denied",
        )
        result = self.diag.analyze_failure(case)
        assert result.category == CATEGORY_AUTH

    def test_data_error(self):
        case = TestCase(
            name="test_item",
            status="failed",
            error_message="KeyError: 'missing_field'",
        )
        result = self.diag.analyze_failure(case)
        assert result.category == CATEGORY_DATA

    def test_unknown_error(self):
        case = TestCase(
            name="test_mystery",
            status="error",
            error_message="Something completely unexpected happened",
        )
        result = self.diag.analyze_failure(case)
        assert result.category == CATEGORY_UNKNOWN
        assert result.confidence == 0.3

    def test_output_used_for_classification(self):
        case = TestCase(
            name="test_example",
            status="error",
            error_message="",
            output="ECONNREFUSED localhost:3000",
        )
        result = self.diag.analyze_failure(case)
        assert result.category == CATEGORY_CONNECTION


class TestLLMDiagnostics:
    def test_llm_used_when_available(self):
        mock_llm = MagicMock()
        mock_llm.available.return_value = True
        mock_response = MagicMock()
        mock_response.content = (
            "ROOT_CAUSE: API endpoint returns wrong status code\n"
            "CATEGORY: assertion\n"
            "SUGGESTION: Update expected status code to 201\n"
            "CONFIDENCE: 0.85\n"
        )
        mock_llm.chat.return_value = mock_response

        diag = FailureDiagnostics(LLMSettings(enabled=True))
        diag._llm_client = mock_llm

        case = TestCase(
            name="test_create_item",
            status="failed",
            error_message="Expected 200 got 201",
        )
        result = diag.analyze_failure(case)

        assert result.category == CATEGORY_ASSERTION
        assert result.confidence == 0.85
        assert "status code" in result.root_cause.lower()
        mock_llm.chat.assert_called_once()

    def test_llm_fallback_on_error(self):
        mock_llm = MagicMock()
        mock_llm.available.return_value = True
        mock_llm.chat.side_effect = Exception("LLM unavailable")

        diag = FailureDiagnostics(LLMSettings(enabled=True))
        diag._llm_client = mock_llm

        case = TestCase(
            name="test_example",
            status="failed",
            error_message="AssertionError: values differ",
        )
        result = diag.analyze_failure(case)

        # Falls back to heuristic
        assert result.category == CATEGORY_ASSERTION

    def test_parse_invalid_llm_response(self):
        mock_llm = MagicMock()
        mock_llm.available.return_value = True
        mock_response = MagicMock()
        mock_response.content = "This is just free text with no structure"
        mock_llm.chat.return_value = mock_response

        diag = FailureDiagnostics(LLMSettings(enabled=True))
        diag._llm_client = mock_llm

        case = TestCase(
            name="test_example",
            status="failed",
            error_message="some error",
        )
        result = diag.analyze_failure(case)

        # Should still return a result, just with defaults
        assert result.category == CATEGORY_UNKNOWN
        assert result.confidence == 0.5


class TestRunSummary:
    def setup_method(self):
        self.diag = FailureDiagnostics(LLMSettings(enabled=False))

    def test_no_failures(self):
        suites = {
            "unit": TestResult(
                suite_name="unit", runner="pytest", passed=5,
                cases=[TestCase(name="t1", status="passed")],
            ),
        }
        summary = self.diag.summarize_run(suites)
        assert summary.total_failures == 0
        assert "passed" in summary.summary_text.lower()

    def test_failures_summarized(self):
        suites = {
            "unit": TestResult(
                suite_name="unit", runner="pytest", passed=2, failed=2,
                cases=[
                    TestCase(name="t1", status="passed"),
                    TestCase(name="t2", status="passed"),
                    TestCase(name="t3", status="failed", error_message="AssertionError: 1 != 2"),
                    TestCase(name="t4", status="failed", error_message="TimeoutError: timed out"),
                ],
            ),
        }
        summary = self.diag.summarize_run(suites)

        assert summary.total_failures == 2
        assert len(summary.diagnostics) == 2
        assert CATEGORY_ASSERTION in summary.categories
        assert CATEGORY_TIMEOUT in summary.categories
        assert "2 test failure" in summary.summary_text

    def test_multi_suite_aggregation(self):
        suites = {
            "unit": TestResult(
                suite_name="unit", runner="pytest", failed=1,
                cases=[
                    TestCase(name="t1", status="failed", error_message="assert False"),
                ],
            ),
            "e2e": TestResult(
                suite_name="e2e", runner="playwright", errors=1,
                cases=[
                    TestCase(name="t2", status="error", error_message="connection refused"),
                ],
            ),
        }
        summary = self.diag.summarize_run(suites)

        assert summary.total_failures == 2
        assert len(summary.diagnostics) == 2

    def test_llm_summary_used_when_available(self):
        mock_llm = MagicMock()
        mock_llm.available.return_value = True
        mock_response = MagicMock()
        mock_response.content = "LLM-generated summary of test failures."
        mock_llm.chat.return_value = mock_response

        diag = FailureDiagnostics(LLMSettings(enabled=True))
        diag._llm_client = mock_llm

        suites = {
            "unit": TestResult(
                suite_name="unit", runner="pytest", failed=1,
                cases=[
                    TestCase(name="t1", status="failed", error_message="assert 1 == 2"),
                ],
            ),
        }
        summary = diag.summarize_run(suites)

        assert summary.summary_text == "LLM-generated summary of test failures."
        # chat called twice: once for analyze_failure, once for summarize_run
        assert mock_llm.chat.call_count == 2
