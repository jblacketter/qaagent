"""Tests for PytestRunner."""
from pathlib import Path
from unittest.mock import patch

from qaagent.runners.pytest_runner import PytestRunner
from qaagent.tools import CmdResult

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "junit"


class TestPytestRunner:
    def test_parse_results(self, tmp_path):
        """Test parsing JUnit XML into TestResult."""
        runner = PytestRunner(output_dir=tmp_path)
        result = runner.parse_results(FIXTURES / "pytest_sample.xml")

        assert result.runner == "pytest"
        assert result.passed == 3
        assert result.failed == 1
        assert result.skipped == 1
        assert result.total == 5
        assert not result.success

    def test_route_mapping_in_parse(self, tmp_path):
        """Test that test names are mapped to routes."""
        runner = PytestRunner(output_dir=tmp_path)
        result = runner.parse_results(FIXTURES / "pytest_sample.xml")

        routes = [c.route for c in result.cases if c.route]
        assert len(routes) > 0
        assert any("GET" in r for r in routes)

    @patch("qaagent.runners.pytest_runner.run_command")
    @patch("qaagent.runners.pytest_runner.which", return_value="/usr/bin/python")
    def test_run_with_junit(self, mock_which, mock_run, tmp_path):
        """Test run() produces a TestResult."""
        import shutil
        # Copy fixture to where runner expects it
        junit_dst = tmp_path / "pytest-junit.xml"
        shutil.copy(FIXTURES / "pytest_sample.xml", junit_dst)

        mock_run.return_value = CmdResult(returncode=1, stdout="FAILED", stderr="")

        runner = PytestRunner(output_dir=tmp_path)
        result = runner.run(tmp_path / "tests")

        assert result.runner == "pytest"
        assert result.returncode == 1
        assert result.passed == 3
        assert result.failed == 1

    @patch("qaagent.runners.pytest_runner.which", return_value=None)
    def test_run_missing_python(self, mock_which, tmp_path):
        """Test graceful failure when python not found."""
        runner = PytestRunner(output_dir=tmp_path)
        result = runner.run(tmp_path / "tests")

        assert result.returncode == -1
        assert result.errors == 1

    @patch("qaagent.runners.pytest_runner.run_command")
    @patch("qaagent.runners.pytest_runner.which", return_value="/usr/bin/python")
    def test_run_no_junit_output(self, mock_which, mock_run, tmp_path):
        """Test handling when pytest produces no JUnit XML."""
        mock_run.return_value = CmdResult(returncode=2, stdout="", stderr="error")

        runner = PytestRunner(output_dir=tmp_path)
        result = runner.run(tmp_path / "tests")

        assert result.returncode == 2
        assert result.errors == 1
        assert len(result.cases) == 0

    @patch("qaagent.runners.pytest_runner.run_command")
    @patch("qaagent.runners.pytest_runner.which", return_value="/usr/bin/python")
    def test_timeout_passed_to_run_command(self, mock_which, mock_run, tmp_path):
        """Test that runner passes timeout to run_command."""
        from qaagent.config.models import RunSettings
        mock_run.return_value = CmdResult(returncode=0, stdout="", stderr="")

        runner = PytestRunner(
            output_dir=tmp_path,
            run_settings=RunSettings(timeout=120),
        )
        runner.run(tmp_path / "tests")

        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == 120
