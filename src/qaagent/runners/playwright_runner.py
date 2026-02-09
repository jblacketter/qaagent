"""Playwright test runner."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from qaagent.runners.base import TestResult, TestRunner
from qaagent.runners.junit_parser import parse_junit_xml
from qaagent.tools import CmdResult, run_command, which

logger = logging.getLogger(__name__)


class PlaywrightRunner(TestRunner):
    """Run Playwright TypeScript tests and parse results."""

    runner_name = "playwright"

    def run(self, test_path: Path, **kwargs: Any) -> TestResult:
        if not which("npx"):
            return TestResult(
                suite_name=test_path.name,
                runner=self.runner_name,
                returncode=-1,
                errors=1,
                cases=[],
            )

        project_dir = test_path
        if test_path.is_file():
            project_dir = test_path.parent

        # Install npm deps if node_modules missing
        node_modules = project_dir / "node_modules"
        if not node_modules.exists() and (project_dir / "package.json").exists():
            logger.info("Installing npm dependencies for Playwright project")
            run_command(["npm", "install"], cwd=project_dir, timeout=120)

        junit_path = self.output_dir / "playwright-junit.xml"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        env = {"PLAYWRIGHT_JUNIT_OUTPUT_FILE": str(junit_path)}
        if self.base_url:
            env["BASE_URL"] = self.base_url

        cmd = [
            "npx", "playwright", "test",
            "--reporter=junit",
        ]

        result = run_command(
            cmd,
            cwd=project_dir,
            timeout=self.run_settings.timeout,
            env=env,
        )

        return self._build_result(test_path.name, result, junit_path)

    def parse_results(self, junit_path: Path, stdout: str = "") -> TestResult:
        cases = parse_junit_xml(junit_path)
        passed = sum(1 for c in cases if c.status == "passed")
        failed = sum(1 for c in cases if c.status == "failed")
        errors = sum(1 for c in cases if c.status == "error")
        skipped = sum(1 for c in cases if c.status == "skipped")
        duration = sum(c.duration for c in cases)

        return TestResult(
            suite_name="playwright",
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
        # Collect additional artifacts
        artifacts = {}

        if junit_path.exists():
            result = self.parse_results(junit_path, cmd_result.stdout)
            result.suite_name = suite_name
            result.returncode = cmd_result.returncode
            artifacts["junit"] = str(junit_path)
        else:
            result = TestResult(
                suite_name=suite_name,
                runner=self.runner_name,
                returncode=cmd_result.returncode,
                errors=1 if cmd_result.returncode != 0 else 0,
                cases=[],
            )

        # Look for test-results directory (screenshots, traces)
        test_results_dir = self.output_dir.parent / "test-results"
        if test_results_dir.exists():
            artifacts["test_results"] = str(test_results_dir)

        result.artifacts = artifacts
        return result
