"""Behave BDD test runner."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from qaagent.runners.base import TestResult, TestRunner
from qaagent.runners.junit_parser import parse_junit_xml
from qaagent.tools import CmdResult, run_command, which

logger = logging.getLogger(__name__)


class BehaveRunner(TestRunner):
    """Run Behave BDD tests and parse results."""

    runner_name = "behave"

    def run(self, test_path: Path, **kwargs: Any) -> TestResult:
        if not which("python"):
            return TestResult(
                suite_name=test_path.name,
                runner=self.runner_name,
                returncode=-1,
                errors=1,
                cases=[],
            )

        junit_dir = self.output_dir / "behave-junit"
        junit_dir.mkdir(parents=True, exist_ok=True)

        abs_test_path = test_path.resolve()
        cmd = [
            "python", "-m", "behave",
            str(abs_test_path),
            f"--junit",
            f"--junit-directory={junit_dir}",
            "--no-capture",
        ]

        result = run_command(
            cmd,
            cwd=abs_test_path.parent if abs_test_path.is_file() else None,
            timeout=self.run_settings.timeout,
        )

        return self._build_result(test_path.name, result, junit_dir)

    def parse_results(self, junit_path: Path, stdout: str = "") -> TestResult:
        # Behave produces one XML file per feature in the junit dir
        all_cases = []
        if junit_path.is_dir():
            for xml_file in sorted(junit_path.glob("*.xml")):
                all_cases.extend(parse_junit_xml(xml_file))
        elif junit_path.is_file():
            all_cases = parse_junit_xml(junit_path)

        passed = sum(1 for c in all_cases if c.status == "passed")
        failed = sum(1 for c in all_cases if c.status == "failed")
        errors = sum(1 for c in all_cases if c.status == "error")
        skipped = sum(1 for c in all_cases if c.status == "skipped")
        duration = sum(c.duration for c in all_cases)

        return TestResult(
            suite_name="behave",
            runner=self.runner_name,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration=duration,
            cases=all_cases,
            artifacts={"junit_dir": str(junit_path)},
            returncode=0 if (failed == 0 and errors == 0) else 1,
        )

    def _build_result(self, suite_name: str, cmd_result: CmdResult, junit_dir: Path) -> TestResult:
        if junit_dir.exists() and any(junit_dir.glob("*.xml")):
            result = self.parse_results(junit_dir, cmd_result.stdout)
            result.suite_name = suite_name
            result.returncode = cmd_result.returncode
            return result

        return TestResult(
            suite_name=suite_name,
            runner=self.runner_name,
            returncode=cmd_result.returncode,
            errors=1 if cmd_result.returncode != 0 else 0,
            cases=[],
        )
