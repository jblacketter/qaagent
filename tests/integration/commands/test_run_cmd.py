"""Integration tests for run CLI commands."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qaagent.commands import app
from qaagent.tools import CmdResult

runner = CliRunner()


def _cmd_result(returncode=0, stdout="OK", stderr=""):
    return CmdResult(returncode=returncode, stdout=stdout, stderr=stderr)


class TestPytestRun:
    def test_help(self):
        result = runner.invoke(app, ["pytest-run", "--help"])
        assert result.exit_code == 0

    def test_success(self, tmp_path):
        with patch("qaagent.commands.run_cmd.which", return_value="/usr/bin/pytest"), \
             patch("qaagent.commands.run_cmd.run_command", return_value=_cmd_result()), \
             patch("qaagent.commands.run_cmd.ensure_dir"):
            result = runner.invoke(app, ["pytest-run", "--outdir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Return code" in result.output

    def test_not_installed(self):
        with patch("qaagent.commands.run_cmd.which", return_value=None):
            result = runner.invoke(app, ["pytest-run"])
        assert result.exit_code == 2
        assert "not installed" in result.output

    def test_json_output(self, tmp_path):
        with patch("qaagent.commands.run_cmd.which", return_value="/usr/bin/pytest"), \
             patch("qaagent.commands.run_cmd.run_command", return_value=_cmd_result()), \
             patch("qaagent.commands.run_cmd.ensure_dir"):
            result = runner.invoke(app, ["pytest-run", "--json-out", "--outdir", str(tmp_path)])
        assert result.exit_code == 0
        assert '"returncode": 0' in result.output

    def test_failure_exit_code(self, tmp_path):
        with patch("qaagent.commands.run_cmd.which", return_value="/usr/bin/pytest"), \
             patch("qaagent.commands.run_cmd.run_command", return_value=_cmd_result(returncode=1, stderr="FAILED")), \
             patch("qaagent.commands.run_cmd.ensure_dir"):
            result = runner.invoke(app, ["pytest-run", "--outdir", str(tmp_path)])
        assert result.exit_code == 1


class TestSchemathesisRun:
    def test_help(self):
        result = runner.invoke(app, ["schemathesis-run", "--help"])
        assert result.exit_code == 0

    def test_not_installed(self):
        with patch("qaagent.commands.run_cmd.which", return_value=None):
            result = runner.invoke(app, ["schemathesis-run"])
        assert result.exit_code == 2
        assert "not installed" in result.output

    def test_no_spec(self):
        with patch("qaagent.commands.run_cmd.which", return_value="/usr/bin/schemathesis"), \
             patch("qaagent.commands.run_cmd.load_config_compat", return_value=None), \
             patch("qaagent.commands.run_cmd.load_active_profile", side_effect=Exception("No profile")), \
             patch("qaagent.commands.run_cmd.find_openapi_candidates", return_value=[]):
            result = runner.invoke(app, ["schemathesis-run"])
        assert result.exit_code == 2
        assert "not provided" in result.output

    def test_no_base_url(self, tmp_path):
        spec = tmp_path / "openapi.json"
        spec.write_text("{}")
        with patch("qaagent.commands.run_cmd.which", return_value="/usr/bin/schemathesis"), \
             patch("qaagent.commands.run_cmd.load_config_compat", return_value=None), \
             patch("qaagent.commands.run_cmd.load_active_profile", side_effect=Exception("No profile")), \
             patch("qaagent.commands.run_cmd.find_openapi_candidates", return_value=[]):
            result = runner.invoke(app, ["schemathesis-run", "--openapi", str(spec)])
        assert result.exit_code == 2
        assert "Base URL" in result.output


class TestPlaywrightInstall:
    def test_help(self):
        result = runner.invoke(app, ["playwright-install", "--help"])
        assert result.exit_code == 0

    def test_not_installed(self):
        with patch("qaagent.commands.run_cmd.module_available", return_value=False):
            result = runner.invoke(app, ["playwright-install"])
        assert result.exit_code == 2
        assert "not installed" in result.output

    def test_success(self):
        with patch("qaagent.commands.run_cmd.module_available", return_value=True), \
             patch("qaagent.commands.run_cmd.run_command", return_value=_cmd_result()):
            result = runner.invoke(app, ["playwright-install"])
        assert result.exit_code == 0


class TestPlaywrightScaffold:
    def test_creates_file(self, tmp_path):
        dest = tmp_path / "tests" / "ui"
        with patch("qaagent.commands.run_cmd.module_available", return_value=True):
            result = runner.invoke(app, ["playwright-scaffold", "--dest", str(dest)])
        assert result.exit_code == 0
        assert "Created" in result.output
        assert (dest / "test_smoke.py").exists()

    def test_file_already_exists(self, tmp_path):
        dest = tmp_path / "tests" / "ui"
        dest.mkdir(parents=True)
        (dest / "test_smoke.py").write_text("# existing")
        with patch("qaagent.commands.run_cmd.module_available", return_value=True):
            result = runner.invoke(app, ["playwright-scaffold", "--dest", str(dest)])
        assert result.exit_code == 0
        assert "already exists" in result.output

    def test_pytest_not_available(self):
        with patch("qaagent.commands.run_cmd.module_available", side_effect=lambda n: n != "pytest"):
            result = runner.invoke(app, ["playwright-scaffold"])
        assert result.exit_code == 2


class TestUiRun:
    def test_help(self):
        result = runner.invoke(app, ["ui-run", "--help"])
        assert result.exit_code == 0

    def test_pytest_not_found(self):
        with patch("qaagent.commands.run_cmd.module_available", return_value=False):
            result = runner.invoke(app, ["ui-run"])
        assert result.exit_code == 2


class TestPerfScaffold:
    def test_creates_locustfile(self, tmp_path):
        dest = tmp_path / "perf"
        result = runner.invoke(app, ["perf-scaffold", "--dest", str(dest)])
        assert result.exit_code == 0
        assert (dest / "locustfile.py").exists()
        assert "Created" in result.output

    def test_file_already_exists(self, tmp_path):
        dest = tmp_path / "perf"
        dest.mkdir(parents=True)
        (dest / "locustfile.py").write_text("# existing")
        result = runner.invoke(app, ["perf-scaffold", "--dest", str(dest)])
        assert result.exit_code == 0
        assert "exists" in result.output


class TestPerfRun:
    def test_help(self):
        result = runner.invoke(app, ["perf-run", "--help"])
        assert result.exit_code == 0

    def test_locust_not_installed(self):
        with patch("qaagent.commands.run_cmd.which", return_value=None):
            result = runner.invoke(app, ["perf-run"])
        assert result.exit_code == 2
        assert "not installed" in result.output

    def test_success(self, tmp_path):
        with patch("qaagent.commands.run_cmd.which", return_value="/usr/bin/locust"), \
             patch("qaagent.commands.run_cmd.run_command", return_value=_cmd_result()), \
             patch("qaagent.commands.run_cmd.ensure_dir"):
            result = runner.invoke(app, ["perf-run", "--outdir", str(tmp_path)])
        assert result.exit_code == 0


class TestLighthouseAudit:
    def test_help(self):
        result = runner.invoke(app, ["lighthouse-audit", "--help"])
        assert result.exit_code == 0

    def test_no_url(self, monkeypatch):
        monkeypatch.delenv("BASE_URL", raising=False)
        result = runner.invoke(app, ["lighthouse-audit"])
        assert result.exit_code == 2

    def test_no_lighthouse_or_npx(self):
        with patch("qaagent.commands.run_cmd.which", return_value=None), \
             patch("qaagent.commands.run_cmd.ensure_dir"):
            result = runner.invoke(app, ["lighthouse-audit", "--url", "https://example.com"])
        assert result.exit_code == 2
        assert "not found" in result.output

    def test_success(self, tmp_path):
        with patch("qaagent.commands.run_cmd.which", return_value="/usr/bin/lighthouse"), \
             patch("qaagent.commands.run_cmd.ensure_dir"), \
             patch("qaagent.commands.run_cmd.run_command", return_value=_cmd_result()):
            result = runner.invoke(app, [
                "lighthouse-audit", "--url", "https://example.com",
                "--outdir", str(tmp_path),
            ])
        assert result.exit_code == 0


class TestA11yRun:
    def test_help(self):
        result = runner.invoke(app, ["a11y-run", "--help"])
        assert result.exit_code == 0

    def test_no_url(self, monkeypatch):
        monkeypatch.delenv("BASE_URL", raising=False)
        result = runner.invoke(app, ["a11y-run"])
        assert result.exit_code == 2

    def test_success(self):
        mock_meta = {"output_markdown": "reports/a11y/report.md", "violations": 3}
        with patch("qaagent.commands.run_cmd.run_axe", return_value=mock_meta):
            result = runner.invoke(app, ["a11y-run", "--url", "https://example.com"])
        assert result.exit_code == 0
        assert "violations" in result.output


class TestA11yFromSitemap:
    def test_help(self):
        result = runner.invoke(app, ["a11y-from-sitemap", "--help"])
        assert result.exit_code == 0

    def test_no_urls_in_sitemap(self):
        with patch("qaagent.commands.run_cmd.fetch_sitemap_urls", return_value=[]):
            result = runner.invoke(app, ["a11y-from-sitemap", "--base-url", "https://example.com"])
        assert result.exit_code == 2
        assert "No URLs" in result.output

    def test_sitemap_error(self):
        with patch("qaagent.commands.run_cmd.fetch_sitemap_urls", side_effect=Exception("HTTP 404")):
            result = runner.invoke(app, ["a11y-from-sitemap", "--base-url", "https://example.com"])
        assert result.exit_code == 2


class TestRunAll:
    def test_help(self):
        result = runner.invoke(app, ["run-all", "--help"])
        assert result.exit_code == 0

    def test_no_active_profile(self):
        # run_all imports load_active_profile locally, so patch at the source module
        with patch("qaagent.config.load_active_profile", side_effect=Exception("No active")):
            result = runner.invoke(app, ["run-all"])
        assert result.exit_code == 2

    def test_success(self):
        mock_profile = MagicMock()
        mock_profile.run.parallel = False
        mock_profile.run.max_workers = None
        mock_entry = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.suites = {}
        mock_result.total_passed = 5
        mock_result.total_failed = 0
        mock_result.total_errors = 0
        mock_result.total_duration = 1.2
        mock_result.diagnostic_summary = None
        mock_result.run_handle = None
        with patch("qaagent.config.load_active_profile", return_value=(mock_entry, mock_profile)), \
             patch("qaagent.runners.orchestrator.RunOrchestrator") as MockOrchestrator:
            MockOrchestrator.return_value.run_all.return_value = mock_result
            result = runner.invoke(app, ["run-all"])
        assert result.exit_code == 0
        assert "ALL PASSED" in result.output
        MockOrchestrator.assert_called_once()
        assert MockOrchestrator.call_args.kwargs["parallel"] is False
        assert MockOrchestrator.call_args.kwargs["max_workers"] is None

    def test_parallel_flag_sets_parallel(self):
        mock_profile = MagicMock()
        mock_profile.run.parallel = False
        mock_profile.run.max_workers = None
        mock_entry = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.suites = {}
        mock_result.total_passed = 1
        mock_result.total_failed = 0
        mock_result.total_errors = 0
        mock_result.total_duration = 0.2
        mock_result.diagnostic_summary = None
        mock_result.run_handle = None

        with patch("qaagent.config.load_active_profile", return_value=(mock_entry, mock_profile)), \
             patch("qaagent.runners.orchestrator.RunOrchestrator") as MockOrchestrator:
            MockOrchestrator.return_value.run_all.return_value = mock_result
            result = runner.invoke(app, ["run-all", "--parallel"])

        assert result.exit_code == 0
        assert "in parallel" in result.output
        assert MockOrchestrator.call_args.kwargs["parallel"] is True

    def test_max_workers_flag_sets_override(self):
        mock_profile = MagicMock()
        mock_profile.run.parallel = False
        mock_profile.run.max_workers = None
        mock_entry = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.suites = {}
        mock_result.total_passed = 1
        mock_result.total_failed = 0
        mock_result.total_errors = 0
        mock_result.total_duration = 0.2
        mock_result.diagnostic_summary = None
        mock_result.run_handle = None

        with patch("qaagent.config.load_active_profile", return_value=(mock_entry, mock_profile)), \
             patch("qaagent.runners.orchestrator.RunOrchestrator") as MockOrchestrator:
            MockOrchestrator.return_value.run_all.return_value = mock_result
            result = runner.invoke(app, ["run-all", "--parallel", "--max-workers", "3"])

        assert result.exit_code == 0
        assert "max workers: 3" in result.output
        assert MockOrchestrator.call_args.kwargs["parallel"] is True
        assert MockOrchestrator.call_args.kwargs["max_workers"] == 3
