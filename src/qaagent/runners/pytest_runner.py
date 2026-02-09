"""Pytest test runner."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from qaagent.runners.base import TestResult, TestRunner
from qaagent.runners.junit_parser import parse_junit_xml
from qaagent.tools import CmdResult, run_command, which

logger = logging.getLogger(__name__)


class PytestRunner(TestRunner):
    """Run pytest tests and parse results."""

    runner_name = "pytest"

    def run(self, test_path: Path, **kwargs: Any) -> TestResult:
        if not which("python"):
            return TestResult(
                suite_name=test_path.name,
                runner=self.runner_name,
                returncode=-1,
                errors=1,
                cases=[],
            )

        junit_path = self.output_dir / "pytest-junit.xml"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        abs_test_path = test_path.resolve()
        cmd = [
            "python", "-m", "pytest",
            str(abs_test_path),
            f"--junitxml={junit_path}",
            "-q",
        ]

        result = run_command(
            cmd,
            cwd=abs_test_path.parent if abs_test_path.is_file() else None,
            timeout=self.run_settings.timeout,
        )

        return self._build_result(test_path.name, result, junit_path)

    def parse_results(self, junit_path: Path, stdout: str = "") -> TestResult:
        cases = parse_junit_xml(junit_path)
        passed = sum(1 for c in cases if c.status == "passed")
        failed = sum(1 for c in cases if c.status == "failed")
        errors = sum(1 for c in cases if c.status == "error")
        skipped = sum(1 for c in cases if c.status == "skipped")
        duration = sum(c.duration for c in cases)

        # Map test names to routes
        for case in cases:
            if case.route is None:
                case.route = self._map_test_to_route(case.name)

        return TestResult(
            suite_name="pytest",
            runner=self.runner_name,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration=duration,
            cases=cases,
            artifacts={"junit": str(junit_path)} if junit_path.exists() else {},
            returncode=0 if (failed == 0 and errors == 0) else 1,
        )

    def _build_result(self, suite_name: str, cmd_result: CmdResult, junit_path: Path) -> TestResult:
        if junit_path.exists():
            result = self.parse_results(junit_path, cmd_result.stdout)
            result.suite_name = suite_name
            result.returncode = cmd_result.returncode
            return result

        # No JUnit file — command may have failed before producing output
        return TestResult(
            suite_name=suite_name,
            runner=self.runner_name,
            returncode=cmd_result.returncode,
            errors=1 if cmd_result.returncode != 0 else 0,
            cases=[],
            artifacts={},
        )
