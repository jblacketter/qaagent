"""Tests for BehaveRunner."""
import shutil
from pathlib import Path
from unittest.mock import patch

from qaagent.runners.behave_runner import BehaveRunner
from qaagent.tools import CmdResult

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "junit"


class TestBehaveRunner:
    def test_parse_results_from_directory(self, tmp_path):
        """Test parsing JUnit XML directory into TestResult."""
        junit_dir = tmp_path / "behave-junit"
        junit_dir.mkdir()
        shutil.copy(FIXTURES / "behave_sample.xml", junit_dir / "TESTS-pets.xml")

        runner = BehaveRunner(output_dir=tmp_path)
        result = runner.parse_results(junit_dir)

        assert result.runner == "behave"
        assert result.passed == 2
        assert result.errors == 1
        assert result.failed == 0
        assert result.skipped == 0
        assert result.returncode == 1  # errors > 0

    def test_parse_results_from_single_file(self, tmp_path):
        """Test parsing a single JUnit XML file."""
        runner = BehaveRunner(output_dir=tmp_path)
        result = runner.parse_results(FIXTURES / "behave_sample.xml")

        assert result.runner == "behave"
        assert result.passed == 2
        assert result.errors == 1
        assert result.total == 3

    def test_parse_results_empty_directory(self, tmp_path):
        """Test parsing empty directory returns zero counts."""
        junit_dir = tmp_path / "empty-junit"
        junit_dir.mkdir()

        runner = BehaveRunner(output_dir=tmp_path)
        result = runner.parse_results(junit_dir)

        assert result.passed == 0
        assert result.failed == 0
        assert result.errors == 0
        assert result.returncode == 0

    @patch("qaagent.runners.behave_runner.run_command")
    @patch("qaagent.runners.behave_runner.which", return_value="/usr/bin/python")
    def test_run_with_junit(self, mock_which, mock_run, tmp_path):
        """Test run() produces a TestResult from JUnit output."""
        junit_dir = tmp_path / "behave-junit"
        junit_dir.mkdir()
        shutil.copy(FIXTURES / "behave_sample.xml", junit_dir / "TESTS-pets.xml")

        mock_run.return_value = CmdResult(returncode=1, stdout="", stderr="")

        runner = BehaveRunner(output_dir=tmp_path)
        result = runner.run(tmp_path / "features")

        assert result.runner == "behave"
        assert result.returncode == 1
        assert result.passed == 2
        assert result.errors == 1

    @patch("qaagent.runners.behave_runner.which", return_value=None)
    def test_run_missing_python(self, mock_which, tmp_path):
        """Test graceful failure when python not found."""
        runner = BehaveRunner(output_dir=tmp_path)
        result = runner.run(tmp_path / "features")

        assert result.returncode == -1
        assert result.errors == 1

    @patch("qaagent.runners.behave_runner.run_command")
    @patch("qaagent.runners.behave_runner.which", return_value="/usr/bin/python")
    def test_run_no_junit_output(self, mock_which, mock_run, tmp_path):
        """Test handling when behave produces no JUnit XML."""
        mock_run.return_value = CmdResult(returncode=2, stdout="", stderr="error")

        runner = BehaveRunner(output_dir=tmp_path)
        result = runner.run(tmp_path / "features")

        assert result.returncode == 2
        assert result.errors == 1
        assert len(result.cases) == 0

    @patch("qaagent.runners.behave_runner.run_command")
    @patch("qaagent.runners.behave_runner.which", return_value="/usr/bin/python")
    def test_timeout_passed_to_run_command(self, mock_which, mock_run, tmp_path):
        """Test that runner passes timeout to run_command."""
        from qaagent.config.models import RunSettings

        mock_run.return_value = CmdResult(returncode=0, stdout="", stderr="")

        runner = BehaveRunner(
            output_dir=tmp_path,
            run_settings=RunSettings(timeout=180),
        )
        runner.run(tmp_path / "features")

        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == 180

    @patch("qaagent.runners.behave_runner.run_command")
    @patch("qaagent.runners.behave_runner.which", return_value="/usr/bin/python")
    def test_run_success(self, mock_which, mock_run, tmp_path):
        """Test successful run with all tests passing."""
        junit_dir = tmp_path / "behave-junit"
        junit_dir.mkdir()
        # Create a simple passing-only JUnit XML
        passing_xml = junit_dir / "TESTS-all_pass.xml"
        passing_xml.write_text(
            '<?xml version="1.0"?>\n'
            '<testsuite name="login" tests="2" errors="0" failures="0" time="0.5">\n'
            '  <testcase classname="login" name="User logs in" time="0.3" />\n'
            '  <testcase classname="login" name="User logs out" time="0.2" />\n'
            "</testsuite>\n"
        )

        mock_run.return_value = CmdResult(returncode=0, stdout="2 passed", stderr="")

        runner = BehaveRunner(output_dir=tmp_path)
        result = runner.run(tmp_path / "features")

        assert result.returncode == 0
        assert result.passed == 2
        assert result.errors == 0
        assert result.failed == 0
