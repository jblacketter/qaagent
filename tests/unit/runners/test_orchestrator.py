"""Tests for RunOrchestrator."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qaagent.config.models import (
    PlaywrightSuiteSettings,
    QAAgentProfile,
    ProjectSettings,
    RunSettings,
    SuiteSettings,
    TestsSettings,
)
from qaagent.runners.base import TestResult
from qaagent.runners.orchestrator import RunOrchestrator, OrchestratorResult


def _disabled_tests() -> TestsSettings:
    return TestsSettings(
        unit=SuiteSettings(enabled=False, output_dir=""),
        behave=SuiteSettings(enabled=False, output_dir=""),
        e2e=PlaywrightSuiteSettings(enabled=False, output_dir=""),
    )


def _make_profile(**overrides) -> QAAgentProfile:
    """Build a minimal QAAgentProfile for tests."""
    defaults = dict(
        project=ProjectSettings(name="test-project", type="api"),
        tests=TestsSettings(
            unit=SuiteSettings(enabled=True, output_dir="tests/unit"),
            behave=SuiteSettings(enabled=False, output_dir="features"),
            e2e=PlaywrightSuiteSettings(enabled=False, output_dir="tests/e2e"),
        ),
        run=RunSettings(retry_count=0, timeout=60, suite_order=["unit", "behave", "e2e"]),
    )
    defaults.update(overrides)
    return QAAgentProfile(**defaults)


def _success_result(suite: str, runner: str = "pytest") -> TestResult:
    return TestResult(
        suite_name=suite,
        runner=runner,
        passed=3,
        failed=0,
        errors=0,
        returncode=0,
        duration=1.5,
    )


def _failure_result(suite: str, runner: str = "pytest") -> TestResult:
    return TestResult(
        suite_name=suite,
        runner=runner,
        passed=2,
        failed=1,
        errors=0,
        returncode=1,
        duration=2.0,
    )


class TestOrchestratorResult:
    def test_success_property(self):
        r = OrchestratorResult()
        assert r.success is True

    def test_failure_property(self):
        r = OrchestratorResult(total_failed=1)
        assert r.success is False

    def test_error_property(self):
        r = OrchestratorResult(total_errors=1)
        assert r.success is False


class TestRunOrchestrator:
    @patch("qaagent.runners.orchestrator.RunManager")
    def test_run_all_single_suite(self, MockRunManager, tmp_path):
        """Run a single enabled suite."""
        mock_handle = MagicMock()
        mock_handle.artifacts_dir = tmp_path / "artifacts"
        mock_handle.artifacts_dir.mkdir()
        MockRunManager.return_value.create_run.return_value = mock_handle

        # Mock the runner class in the _RUNNER_MAP
        mock_runner_cls = MagicMock()
        mock_runner_inst = MagicMock()
        mock_runner_inst.run.return_value = _success_result("unit")
        mock_runner_cls.return_value = mock_runner_inst

        profile = _make_profile()
        test_dir = tmp_path / "tests" / "unit"
        test_dir.mkdir(parents=True)
        profile.tests.unit.output_dir = str(test_dir)

        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        with patch.dict("qaagent.runners.orchestrator._RUNNER_MAP", {"unit": mock_runner_cls}):
            result = orch.run_all()

        assert "unit" in result.suites
        assert result.total_passed == 3
        assert result.total_failed == 0
        assert result.success
        mock_handle.finalize.assert_called_once()

    @patch("qaagent.runners.orchestrator.RunManager")
    def test_run_all_skips_disabled(self, MockRunManager, tmp_path):
        """Disabled suites are skipped."""
        MockRunManager.return_value.create_run.return_value = MagicMock()

        profile = _make_profile(tests=_disabled_tests())

        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        result = orch.run_all()

        assert len(result.suites) == 0
        assert result.success

    @patch("qaagent.runners.orchestrator.RunManager")
    def test_retry_on_failure(self, MockRunManager, tmp_path):
        """Failed suites are retried."""
        mock_handle = MagicMock()
        mock_handle.artifacts_dir = tmp_path / "artifacts"
        mock_handle.artifacts_dir.mkdir()
        MockRunManager.return_value.create_run.return_value = mock_handle

        fail_result = _failure_result("unit")
        success_result = _success_result("unit")
        mock_runner_cls = MagicMock()
        mock_runner_inst = MagicMock()
        mock_runner_inst.run.side_effect = [fail_result, success_result]
        mock_runner_cls.return_value = mock_runner_inst

        profile = _make_profile(
            run=RunSettings(retry_count=1, timeout=60, suite_order=["unit", "behave", "e2e"]),
        )
        test_dir = tmp_path / "tests" / "unit"
        test_dir.mkdir(parents=True)
        profile.tests.unit.output_dir = str(test_dir)

        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        with patch.dict("qaagent.runners.orchestrator._RUNNER_MAP", {"unit": mock_runner_cls}):
            result = orch.run_all()

        assert mock_runner_inst.run.call_count == 2
        assert result.suites["unit"].success

    @patch("qaagent.runners.orchestrator.RunManager")
    def test_aggregates_totals(self, MockRunManager, tmp_path):
        """Totals are aggregated across suites."""
        mock_handle = MagicMock()
        mock_handle.artifacts_dir = tmp_path / "artifacts"
        mock_handle.artifacts_dir.mkdir()
        MockRunManager.return_value.create_run.return_value = mock_handle

        mock_runner_cls = MagicMock()
        mock_runner_inst = MagicMock()
        mock_runner_inst.run.return_value = TestResult(
            suite_name="unit", runner="pytest",
            passed=5, failed=2, errors=1, returncode=1, duration=3.0,
        )
        mock_runner_cls.return_value = mock_runner_inst

        profile = _make_profile()
        test_dir = tmp_path / "tests" / "unit"
        test_dir.mkdir(parents=True)
        profile.tests.unit.output_dir = str(test_dir)

        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        with patch.dict("qaagent.runners.orchestrator._RUNNER_MAP", {"unit": mock_runner_cls}):
            result = orch.run_all()

        assert result.total_passed == 5
        assert result.total_failed == 2
        assert result.total_errors == 1
        assert result.total_duration == 3.0
        assert not result.success

    @patch("qaagent.runners.orchestrator.RunManager")
    def test_run_suite_unknown_runner(self, MockRunManager, tmp_path):
        """Unknown suite names return an error result."""
        MockRunManager.return_value.create_run.return_value = MagicMock()

        profile = _make_profile()
        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        result = orch.run_suite("unknown_suite", tmp_path)

        assert result.errors == 1
        assert result.returncode == -1

    @patch("qaagent.runners.orchestrator.RunManager")
    def test_missing_test_path_skips(self, MockRunManager, tmp_path):
        """Suites with missing test paths are skipped."""
        mock_handle = MagicMock()
        MockRunManager.return_value.create_run.return_value = mock_handle

        profile = _make_profile()
        profile.tests.unit.output_dir = str(tmp_path / "nonexistent")

        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        result = orch.run_all()

        assert len(result.suites) == 0

    @patch("qaagent.runners.orchestrator.RunManager")
    def test_evidence_handle_created(self, MockRunManager, tmp_path):
        """Evidence RunHandle is created and assigned to result."""
        mock_handle = MagicMock()
        MockRunManager.return_value.create_run.return_value = mock_handle

        profile = _make_profile(tests=_disabled_tests())

        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        result = orch.run_all()

        assert result.run_handle is mock_handle
        MockRunManager.return_value.create_run.assert_called_once()
        mock_handle.finalize.assert_called_once()

    @patch("qaagent.runners.orchestrator.RunManager")
    def test_suite_order_respected(self, MockRunManager, tmp_path):
        """Suites are run in the configured order."""
        mock_handle = MagicMock()
        mock_handle.artifacts_dir = tmp_path / "artifacts"
        mock_handle.artifacts_dir.mkdir()
        MockRunManager.return_value.create_run.return_value = mock_handle

        call_order = []

        def make_runner_cls(name):
            cls = MagicMock()
            inst = MagicMock()
            def run_fn(test_path):
                call_order.append(name)
                return _success_result(name)
            inst.run.side_effect = run_fn
            cls.return_value = inst
            return cls

        profile = _make_profile(
            tests=TestsSettings(
                unit=SuiteSettings(enabled=True, output_dir=str(tmp_path / "unit")),
                behave=SuiteSettings(enabled=True, output_dir=str(tmp_path / "behave")),
                e2e=PlaywrightSuiteSettings(enabled=True, output_dir=str(tmp_path / "e2e")),
            ),
            run=RunSettings(suite_order=["e2e", "unit", "behave"]),
        )
        (tmp_path / "unit").mkdir()
        (tmp_path / "behave").mkdir()
        (tmp_path / "e2e").mkdir()

        runner_map = {
            "unit": make_runner_cls("unit"),
            "behave": make_runner_cls("behave"),
            "e2e": make_runner_cls("e2e"),
        }

        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        with patch.dict("qaagent.runners.orchestrator._RUNNER_MAP", runner_map):
            result = orch.run_all()

        assert call_order == ["e2e", "unit", "behave"]
        assert len(result.suites) == 3

    def test_external_handle_used_and_not_finalized(self, tmp_path):
        """When an external RunHandle is provided, it is used and NOT finalized."""
        external_handle = MagicMock()
        external_handle.artifacts_dir = tmp_path / "artifacts"
        external_handle.artifacts_dir.mkdir()

        mock_runner_cls = MagicMock()
        mock_runner_inst = MagicMock()
        mock_runner_inst.run.return_value = _success_result("unit")
        mock_runner_cls.return_value = mock_runner_inst

        profile = _make_profile()
        test_dir = tmp_path / "tests" / "unit"
        test_dir.mkdir(parents=True)
        profile.tests.unit.output_dir = str(test_dir)

        orch = RunOrchestrator(config=profile, output_dir=tmp_path, run_handle=external_handle)
        with patch.dict("qaagent.runners.orchestrator._RUNNER_MAP", {"unit": mock_runner_cls}):
            result = orch.run_all()

        assert result.run_handle is external_handle
        assert result.total_passed == 3
        # External handle should NOT be finalized by orchestrator
        external_handle.finalize.assert_not_called()
        # But counts should still be updated
        external_handle.increment_count.assert_any_call("test_suites", 1)
        external_handle.increment_count.assert_any_call("tests_passed", 3)

    @patch("qaagent.runners.orchestrator.EvidenceWriter")
    @patch("qaagent.runners.orchestrator.EvidenceIDGenerator")
    @patch("qaagent.runners.orchestrator.RunManager")
    def test_writes_test_records(self, MockRunManager, MockIDGen, MockWriter, tmp_path):
        """TestRecord evidence is written per test case."""
        from qaagent.runners.base import TestCase as TC

        mock_handle = MagicMock()
        mock_handle.artifacts_dir = tmp_path / "artifacts"
        mock_handle.artifacts_dir.mkdir()
        mock_handle.run_id = "20260208_120000Z"
        MockRunManager.return_value.create_run.return_value = mock_handle

        mock_id_gen = MagicMock()
        mock_id_gen.next_id.side_effect = lambda prefix: f"TST-001"
        MockIDGen.return_value = mock_id_gen

        mock_writer_inst = MagicMock()
        MockWriter.return_value = mock_writer_inst

        mock_runner_cls = MagicMock()
        mock_runner_inst = MagicMock()
        mock_runner_inst.run.return_value = TestResult(
            suite_name="unit", runner="pytest",
            passed=1, failed=1, returncode=1, duration=2.0,
            cases=[
                TC(name="test_pass", status="passed", duration=1.0),
                TC(name="test_fail", status="failed", duration=1.0, error_message="assert False"),
            ],
        )
        mock_runner_cls.return_value = mock_runner_inst

        profile = _make_profile()
        test_dir = tmp_path / "tests" / "unit"
        test_dir.mkdir(parents=True)
        profile.tests.unit.output_dir = str(test_dir)

        orch = RunOrchestrator(config=profile, output_dir=tmp_path)
        with patch.dict("qaagent.runners.orchestrator._RUNNER_MAP", {"unit": mock_runner_cls}):
            result = orch.run_all()

        # EvidenceWriter.write_records should have been called with test records
        mock_writer_inst.write_records.assert_called_once()
        call_args = mock_writer_inst.write_records.call_args
        assert call_args[0][0] == "tests"
        records = call_args[0][1]
        assert len(records) == 2
        assert records[0]["name"] == "test_pass"
        assert records[1]["status"] == "failed"
