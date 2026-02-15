"""Integration tests for record CLI command."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qaagent.commands import app
from qaagent.config.models import AuthSettings, EnvironmentSettings, ProjectSettings, QAAgentProfile
from qaagent.recording.models import RecordedFlow

runner = CliRunner()


class TestRecordCommand:
    def test_help(self):
        result = runner.invoke(app, ["record", "--help"])
        assert result.exit_code == 0

    def test_requires_url_or_active_profile(self):
        with patch("qaagent.commands.record_cmd.load_active_profile", side_effect=Exception("No active")):
            result = runner.invoke(app, ["record"])
        assert result.exit_code == 2
        assert "Provide --url" in result.output

    def test_records_and_exports(self, tmp_path):
        flow = RecordedFlow(name="demo", start_url="https://app.example.com", actions=[], created_at="2026-02-15T00:00:00Z")
        recording_path = tmp_path / "recording.json"
        pw_path = tmp_path / "recorded_demo.spec.ts"
        feature_path = tmp_path / "recorded_demo.feature"
        steps_path = tmp_path / "recorded_steps.py"

        with patch("qaagent.commands.record_cmd.record_flow", return_value=flow) as mock_record, \
             patch("qaagent.commands.record_cmd.save_recording", return_value=recording_path), \
             patch("qaagent.commands.record_cmd.export_playwright_spec", return_value=pw_path), \
             patch("qaagent.commands.record_cmd.export_behave_assets", return_value=(feature_path, steps_path)):
            result = runner.invoke(
                app,
                [
                    "record",
                    "--url",
                    "https://app.example.com",
                    "--name",
                    "demo",
                    "--out-dir",
                    str(tmp_path),
                ],
            )

        assert result.exit_code == 0
        kwargs = mock_record.call_args.kwargs
        assert kwargs["start_url"] == "https://app.example.com"
        assert kwargs["name"] == "demo"
        assert "Recording Summary" in result.output

    def test_uses_profile_defaults_for_auth_headers(self, tmp_path):
        flow = RecordedFlow(name="demo", start_url="https://secure.example.com", actions=[], created_at="2026-02-15T00:00:00Z")
        entry = MagicMock()
        entry.resolved_path.return_value = tmp_path
        profile = QAAgentProfile(
            project=ProjectSettings(name="demo", type="web"),
            app={
                "dev": EnvironmentSettings(
                    base_url="https://secure.example.com",
                    headers={"X-Tenant": "acme"},
                    auth=AuthSettings(header_name="Authorization", token_env="API_TOKEN", prefix="Bearer "),
                )
            },
        )

        with patch("qaagent.commands.record_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.commands.record_cmd.record_flow", return_value=flow) as mock_record, \
             patch("qaagent.commands.record_cmd.save_recording", return_value=tmp_path / "recording.json"), \
             patch("qaagent.commands.record_cmd.export_playwright_spec", return_value=tmp_path / "spec.ts"), \
             patch("qaagent.commands.record_cmd.export_behave_assets", return_value=(tmp_path / "feature.feature", tmp_path / "steps.py")):
            result = runner.invoke(app, ["record"], env={"API_TOKEN": "secret"})

        assert result.exit_code == 0
        kwargs = mock_record.call_args.kwargs
        assert kwargs["start_url"] == "https://secure.example.com"
        assert kwargs["headers"]["X-Tenant"] == "acme"
        assert kwargs["headers"]["Authorization"] == "Bearer secret"

