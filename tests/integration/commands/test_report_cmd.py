"""Integration tests for report CLI commands."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qaagent.commands import app

runner = CliRunner()


class TestReport:
    def test_help(self):
        result = runner.invoke(app, ["report", "--help"])
        assert result.exit_code == 0

    def test_success(self):
        mock_result = {"output": "reports/findings.md", "summary": "2 findings"}
        with patch("qaagent.commands.report_cmd.generate_report", return_value=mock_result):
            result = runner.invoke(app, ["report"])
        assert result.exit_code == 0
        assert "Report written" in result.output

    def test_json_output(self):
        mock_result = {"output": "reports/findings.md", "summary": "2 findings"}
        with patch("qaagent.commands.report_cmd.generate_report", return_value=mock_result):
            result = runner.invoke(app, ["report", "--json-out"])
        assert result.exit_code == 0
        assert '"output"' in result.output

    def test_html_format_flips_extension(self):
        mock_result = {"output": "reports/findings.html", "summary": "OK"}
        with patch("qaagent.commands.report_cmd.generate_report", return_value=mock_result) as mock_gen:
            runner.invoke(app, ["report", "--fmt", "html"])
        # Should have flipped .md to .html in the output argument
        call_kwargs = mock_gen.call_args
        assert call_kwargs.kwargs.get("output", call_kwargs.args[0] if call_kwargs.args else "").endswith(".html")


class TestDashboard:
    def test_help(self):
        result = runner.invoke(app, ["dashboard", "--help"])
        assert result.exit_code == 0

    def test_no_active_target(self):
        with patch("qaagent.commands.report_cmd.load_active_profile", side_effect=Exception("No active")):
            result = runner.invoke(app, ["dashboard"])
        assert result.exit_code == 2

    def test_success(self):
        entry = MagicMock()
        entry.name = "myapp"
        profile = MagicMock()
        with patch("qaagent.commands.report_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.dashboard.generate_dashboard_from_workspace", return_value=Path("/tmp/dashboard.html")):
            result = runner.invoke(app, ["dashboard"])
        assert result.exit_code == 0
        assert "Dashboard generated" in result.output

    def test_generation_error(self):
        entry = MagicMock()
        entry.name = "myapp"
        profile = MagicMock()
        with patch("qaagent.commands.report_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.dashboard.generate_dashboard_from_workspace", side_effect=Exception("No data")):
            result = runner.invoke(app, ["dashboard"])
        assert result.exit_code == 1


class TestSummarize:
    def test_help(self):
        result = runner.invoke(app, ["summarize", "--help"])
        assert result.exit_code == 0

    def test_success(self, tmp_path):
        out_file = tmp_path / "summary.md"
        mock_meta = {"output": "reports/findings.md", "summary": "OK"}
        with patch("qaagent.commands.report_cmd.generate_report", return_value=mock_meta), \
             patch("qaagent.commands.report_cmd.summarize_findings_text", return_value="Executive summary here"), \
             patch("qaagent.commands.report_cmd.llm_available", return_value=False):
            result = runner.invoke(app, ["summarize", "--out", str(out_file)])
        assert result.exit_code == 0
        assert "Summary written" in result.output
        assert out_file.exists()


class TestNotify:
    def test_help(self):
        result = runner.invoke(app, ["notify", "--help"])
        assert result.exit_code == 0

    def test_prints_summary_without_targets(self):
        meta = {
            "output": "reports/findings.md",
            "format": "markdown",
            "summary": {"tests": 4, "failures": 0, "errors": 0, "skipped": 0, "time": 1.2},
            "extras": {},
        }
        with patch("qaagent.commands.report_cmd.generate_report", return_value=meta):
            result = runner.invoke(app, ["notify"])

        assert result.exit_code == 0
        assert "Status: PASSED" in result.output
        assert "No notification targets configured" in result.output

    def test_json_output(self):
        meta = {
            "output": "reports/findings.md",
            "format": "markdown",
            "summary": {"tests": 4, "failures": 1, "errors": 0, "skipped": 0, "time": 1.2},
            "extras": {},
        }
        with patch("qaagent.commands.report_cmd.generate_report", return_value=meta):
            result = runner.invoke(app, ["notify", "--output-format", "json"])

        assert result.exit_code == 0
        assert '"status": "failed"' in result.output

    def test_dry_run_skips_sending(self):
        meta = {
            "output": "reports/findings.md",
            "format": "markdown",
            "summary": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "time": 0.2},
            "extras": {},
        }
        with patch("qaagent.commands.report_cmd.generate_report", return_value=meta), \
             patch("qaagent.commands.report_cmd.send_slack_webhook") as mock_slack, \
             patch("qaagent.commands.report_cmd.send_email_smtp") as mock_email:
            result = runner.invoke(
                app,
                ["notify", "--dry-run", "--slack-webhook", "https://example.com", "--email-to", "qa@example.com"],
            )

        assert result.exit_code == 0
        mock_slack.assert_not_called()
        mock_email.assert_not_called()

    def test_sends_slack_and_email(self):
        meta = {
            "output": "reports/findings.md",
            "format": "markdown",
            "summary": {"tests": 3, "failures": 0, "errors": 0, "skipped": 0, "time": 0.4},
            "extras": {},
        }
        with patch("qaagent.commands.report_cmd.generate_report", return_value=meta), \
             patch("qaagent.commands.report_cmd.send_slack_webhook") as mock_slack, \
             patch("qaagent.commands.report_cmd.send_email_smtp") as mock_email:
            result = runner.invoke(
                app,
                [
                    "notify",
                    "--slack-webhook",
                    "https://example.com",
                    "--email-to",
                    "qa@example.com",
                    "--smtp-host",
                    "smtp.example.com",
                    "--smtp-user",
                    "user",
                    "--email-from",
                    "from@example.com",
                ],
                env={"QAAGENT_SMTP_PASSWORD": "secret"},
            )

        assert result.exit_code == 0
        mock_slack.assert_called_once()
        mock_email.assert_called_once()

    def test_email_requires_smtp_configuration(self):
        meta = {
            "output": "reports/findings.md",
            "format": "markdown",
            "summary": {"tests": 3, "failures": 0, "errors": 0, "skipped": 0, "time": 0.4},
            "extras": {},
        }
        with patch("qaagent.commands.report_cmd.generate_report", return_value=meta):
            result = runner.invoke(app, ["notify", "--email-to", "qa@example.com"])

        assert result.exit_code == 2
        assert "Email notification requires" in result.output


class TestOpenReport:
    def test_help(self):
        result = runner.invoke(app, ["open-report", "--help"])
        assert result.exit_code == 0

    def test_file_not_found(self, tmp_path):
        missing = tmp_path / "nonexistent.html"
        result = runner.invoke(app, ["open-report", "--path", str(missing)])
        assert result.exit_code == 2
        assert "not found" in result.output

    def test_success(self, tmp_path):
        report_file = tmp_path / "report.html"
        report_file.write_text("<html></html>")
        with patch("qaagent.commands.report_cmd.webbrowser") as mock_wb:
            result = runner.invoke(app, ["open-report", "--path", str(report_file)])
        assert result.exit_code == 0
        assert "Opened" in result.output
        mock_wb.open.assert_called_once()


class TestExportReports:
    def test_help(self):
        result = runner.invoke(app, ["export-reports", "--help"])
        assert result.exit_code == 0

    def test_dir_not_found(self, tmp_path):
        missing = tmp_path / "no_reports"
        result = runner.invoke(app, ["export-reports", "--reports-dir", str(missing)])
        assert result.exit_code == 2
        assert "not found" in result.output

    def test_success(self, tmp_path):
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        (reports_dir / "findings.md").write_text("# Findings")
        out_zip = tmp_path / "export.zip"
        result = runner.invoke(app, [
            "export-reports",
            "--reports-dir", str(reports_dir),
            "--out-zip", str(out_zip),
        ])
        assert result.exit_code == 0
        assert "Exported" in result.output
        assert out_zip.exists()


class TestPlanRun:
    def test_help(self):
        result = runner.invoke(app, ["plan-run", "--help"])
        assert result.exit_code == 0
