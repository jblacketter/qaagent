"""Test orchestration engine.

Runs enabled test suites in configured order, retries failures,
collects artifacts, and writes evidence.
"""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from qaagent.config.models import LLMSettings, QAAgentProfile, RunSettings
from qaagent.evidence.id_generator import EvidenceIDGenerator
from qaagent.evidence.models import TestRecord
from qaagent.evidence.run_manager import RunHandle, RunManager
from qaagent.evidence.writer import EvidenceWriter
from qaagent.generators.base import GenerationResult
from qaagent.runners.base import TestCase, TestResult, TestRunner
from qaagent.runners.behave_runner import BehaveRunner
from qaagent.runners.diagnostics import FailureDiagnostics, RunDiagnosticSummary
from qaagent.runners.playwright_runner import PlaywrightRunner
from qaagent.runners.pytest_runner import PytestRunner

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    """Aggregated result from running all test suites."""
    suites: Dict[str, TestResult] = field(default_factory=dict)
    total_passed: int = 0
    total_failed: int = 0
    total_errors: int = 0
    total_duration: float = 0.0
    artifacts: Dict[str, str] = field(default_factory=dict)
    run_handle: Optional[RunHandle] = None
    diagnostic_summary: Optional[RunDiagnosticSummary] = None

    @property
    def success(self) -> bool:
        return self.total_failed == 0 and self.total_errors == 0


# Map suite names to runner classes
_RUNNER_MAP = {
    "unit": PytestRunner,
    "behave": BehaveRunner,
    "e2e": PlaywrightRunner,
}

# Default test paths per suite when GenerationResult not provided
_DEFAULT_PATHS = {
    "unit": "tests/unit",
    "behave": "features",
    "e2e": "tests/e2e",
}


class RunOrchestrator:
    """Orchestrate test suite execution."""

    def __init__(
        self,
        config: QAAgentProfile,
        output_dir: Optional[Path] = None,
        run_handle: Optional[RunHandle] = None,
    ) -> None:
        self.config = config
        self.output_dir = output_dir or Path("reports")
        self.run_settings = config.run
        self._external_handle = run_handle

    def run_all(
        self,
        generated: Optional[Dict[str, GenerationResult]] = None,
    ) -> OrchestratorResult:
        """Run all enabled suites in configured order.

        Args:
            generated: Optional mapping of suite name to GenerationResult,
                       used to locate generated test files.

        Returns:
            OrchestratorResult with per-suite results and evidence handle.
        """
        # Use external handle if provided, otherwise create one
        owns_handle = self._external_handle is None
        handle = self._external_handle or self._create_run_handle()
        result = OrchestratorResult(run_handle=handle)

        base_url = self._resolve_base_url()

        for suite_name in self.run_settings.suite_order:
            if not self._suite_enabled(suite_name):
                logger.info("Suite '%s' is disabled, skipping", suite_name)
                continue

            test_path = self._resolve_test_path(suite_name, generated)
            if test_path is None or not test_path.exists():
                logger.info("Suite '%s': test path not found, skipping", suite_name)
                continue

            logger.info("Running suite '%s' from %s", suite_name, test_path)
            suite_result = self.run_suite(suite_name, test_path, base_url)

            # Retry failed tests if configured
            if not suite_result.success and self.run_settings.retry_count > 0:
                suite_result = self._retry_failed(
                    suite_name, test_path, base_url, suite_result,
                )

            result.suites[suite_name] = suite_result
            result.total_passed += suite_result.passed
            result.total_failed += suite_result.failed
            result.total_errors += suite_result.errors
            result.total_duration += suite_result.duration

            # Collect artifacts and write test records into evidence
            self._collect_artifacts(handle, suite_name, suite_result)
            self._write_test_records(handle, suite_name, suite_result)

        # Run diagnostics on failures
        if not result.success:
            result.diagnostic_summary = self._run_diagnostics(result.suites)

        # Update evidence counts; only finalize if we own the handle
        if handle:
            handle.increment_count("test_suites", len(result.suites))
            handle.increment_count("tests_passed", result.total_passed)
            handle.increment_count("tests_failed", result.total_failed)
            if result.diagnostic_summary:
                handle.add_diagnostic(result.diagnostic_summary.summary_text)
            if owns_handle:
                handle.finalize()

        return result

    def run_suite(
        self,
        suite_name: str,
        test_path: Path,
        base_url: Optional[str] = None,
    ) -> TestResult:
        """Run a single test suite."""
        runner_cls = _RUNNER_MAP.get(suite_name)
        if runner_cls is None:
            logger.warning("No runner found for suite '%s'", suite_name)
            return TestResult(
                suite_name=suite_name,
                runner="unknown",
                returncode=-1,
                errors=1,
            )

        suite_settings = self._get_suite_settings(suite_name)
        suite_output = self.output_dir / suite_name
        suite_output.mkdir(parents=True, exist_ok=True)

        runner = runner_cls(
            suite_settings=suite_settings,
            run_settings=self.run_settings,
            base_url=base_url or self._resolve_base_url(),
            output_dir=suite_output,
        )

        return runner.run(test_path)

    def _retry_failed(
        self,
        suite_name: str,
        test_path: Path,
        base_url: Optional[str],
        previous: TestResult,
    ) -> TestResult:
        """Retry failed tests up to configured max."""
        best = previous
        for attempt in range(1, self.run_settings.retry_count + 1):
            if best.success:
                break
            logger.info(
                "Retrying suite '%s' (attempt %d/%d)",
                suite_name, attempt, self.run_settings.retry_count,
            )
            retry_result = self.run_suite(suite_name, test_path, base_url)
            if retry_result.failed < best.failed:
                best = retry_result
        return best

    def _create_run_handle(self) -> Optional[RunHandle]:
        """Create a RunHandle for evidence collection."""
        try:
            manager = RunManager()
            return manager.create_run(
                target_name=self.config.project.name,
                target_path=Path.cwd(),
            )
        except Exception:
            logger.warning("Could not create evidence run handle")
            return None

    def _resolve_base_url(self) -> Optional[str]:
        """Get base_url from config."""
        import os
        for env_settings in self.config.app.values():
            if env_settings.base_url:
                return env_settings.base_url
        return os.environ.get("BASE_URL")

    def _suite_enabled(self, suite_name: str) -> bool:
        """Check if a suite is enabled in config."""
        suite = self._get_suite_settings(suite_name)
        if suite is None:
            return False
        return suite.enabled

    def _get_suite_settings(self, suite_name: str):
        """Get SuiteSettings for a suite name."""
        tests = self.config.tests
        mapping = {
            "unit": tests.unit,
            "behave": tests.behave,
            "e2e": tests.e2e,
        }
        return mapping.get(suite_name)

    def _resolve_test_path(
        self,
        suite_name: str,
        generated: Optional[Dict[str, GenerationResult]],
    ) -> Optional[Path]:
        """Determine test path from GenerationResult or defaults."""
        if generated and suite_name in generated:
            gen = generated[suite_name]
            # Use the output directory from the first generated file
            if gen.files:
                first_path = next(iter(gen.files.values()))
                return first_path.parent

        suite = self._get_suite_settings(suite_name)
        if suite and suite.output_dir:
            return Path(suite.output_dir)

        default = _DEFAULT_PATHS.get(suite_name)
        return Path(default) if default else None

    def _run_diagnostics(
        self,
        suites: Dict[str, TestResult],
    ) -> Optional[RunDiagnosticSummary]:
        """Run failure diagnostics if there are failures."""
        try:
            llm_settings = getattr(self.config, "llm", LLMSettings())
            diag = FailureDiagnostics(llm_settings=llm_settings)
            return diag.summarize_run(suites)
        except Exception:
            logger.warning("Diagnostics failed", exc_info=True)
            return None

    def _write_test_records(
        self,
        handle: Optional[RunHandle],
        suite_name: str,
        result: TestResult,
    ) -> None:
        """Write a TestRecord per test case into evidence."""
        if handle is None or not result.cases:
            return

        try:
            id_gen = EvidenceIDGenerator(handle.run_id)
            writer = EvidenceWriter(handle)
            records = []
            for case in result.cases:
                record = TestRecord(
                    test_id=id_gen.next_id("tst"),
                    kind=suite_name,
                    name=case.name,
                    status=case.status,
                    suite_name=suite_name,
                    runner_type=result.runner,
                    duration=case.duration,
                    route=case.route,
                    error_message=case.error_message,
                )
                records.append(record.to_dict())
            writer.write_records("tests", records)
        except Exception:
            logger.warning("Could not write test records to evidence", exc_info=True)

    def _collect_artifacts(
        self,
        handle: Optional[RunHandle],
        suite_name: str,
        result: TestResult,
    ) -> None:
        """Copy test artifacts into evidence run directory."""
        if handle is None:
            return

        for artifact_name, artifact_path_str in result.artifacts.items():
            artifact_path = Path(artifact_path_str)
            if artifact_path.exists():
                dest = handle.artifacts_dir / suite_name / artifact_name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if artifact_path.is_dir():
                    shutil.copytree(artifact_path, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(artifact_path, dest)
