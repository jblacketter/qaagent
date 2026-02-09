"""Tests for PlaywrightRunner."""
from pathlib import Path
from unittest.mock import patch

from qaagent.runners.playwright_runner import PlaywrightRunner
from qaagent.tools import CmdResult

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "junit"


class TestPlaywrightRunner:
    def test_parse_results(self, tmp_path):
        """Test parsing Playwright JUnit XML."""
        runner = PlaywrightRunner(output_dir=tmp_path)
        result = runner.parse_results(FIXTURES / "playwright_sample.xml")

        assert result.runner == "playwright"
        assert result.passed == 2
        assert result.failed == 1
        assert result.total == 3

    @patch("qaagent.runners.playwright_runner.which", return_value=None)
    def test_run_missing_npx(self, mock_which, tmp_path):
        """Test graceful failure when npx not found."""
        runner = PlaywrightRunner(output_dir=tmp_path)
        result = runner.run(tmp_path)

        assert result.returncode == -1
        assert result.errors == 1

    @patch("qaagent.runners.playwright_runner.run_command")
    @patch("qaagent.runners.playwright_runner.which", return_value="/usr/bin/npx")
    def test_run_passes_base_url(self, mock_which, mock_run, tmp_path):
        """Test that BASE_URL env var is passed."""
        mock_run.return_value = CmdResult(returncode=0, stdout="", stderr="")

        runner = PlaywrightRunner(output_dir=tmp_path, base_url="http://localhost:3000")
        runner.run(tmp_path)

        call_args = mock_run.call_args
        env = call_args[1].get("env") or call_args.kwargs.get("env")
        assert env["BASE_URL"] == "http://localhost:3000"

    @patch("qaagent.runners.playwright_runner.run_command")
    @patch("qaagent.runners.playwright_runner.which", return_value="/usr/bin/npx")
    def test_run_installs_deps(self, mock_which, mock_run, tmp_path):
        """Test npm install when node_modules missing."""
        # Create package.json but no node_modules
        (tmp_path / "package.json").write_text("{}")
        mock_run.return_value = CmdResult(returncode=0, stdout="", stderr="")

        runner = PlaywrightRunner(output_dir=tmp_path)
        runner.run(tmp_path)

        # Should have called npm install first, then npx playwright test
        assert mock_run.call_count == 2
        first_call = mock_run.call_args_list[0]
        assert "npm" in first_call[0][0]
