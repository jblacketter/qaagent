"""Integration tests for analyze CLI commands."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qaagent.commands import app
from qaagent.config.models import (
    AuthSettings,
    EnvironmentSettings,
    OpenAPISettings,
    ProjectSettings,
    QAAgentProfile,
)

runner = CliRunner()


class TestAnalyzeCoverageGaps:
    def test_help(self):
        result = runner.invoke(app, ["analyze", "coverage-gaps", "--help"])
        assert result.exit_code == 0

    def test_requires_inputs_or_active_profile(self):
        with patch("qaagent.commands.analyze_cmd.load_active_profile", side_effect=Exception("No active")):
            result = runner.invoke(app, ["analyze", "coverage-gaps"])
        assert result.exit_code == 2
        assert "Provide --routes-file or --openapi" in result.output

    def test_explicit_openapi_and_junit(self, tmp_path):
        root = Path.cwd()
        out_file = tmp_path / "coverage_gaps.json"
        markdown = tmp_path / "coverage_gaps.md"

        result = runner.invoke(
            app,
            [
                "analyze",
                "coverage-gaps",
                "--openapi",
                str(root / "tests/fixtures/data/openapi.yaml"),
                "--junit",
                str(root / "tests/fixtures/data/junit_schemathesis.xml"),
                "--out",
                str(out_file),
                "--markdown",
                str(markdown),
            ],
        )

        assert result.exit_code == 0
        assert out_file.exists()
        assert markdown.exists()
        payload = json.loads(out_file.read_text())
        assert payload["total"] == 2
        assert payload["covered"] == 1
        assert payload["pct"] == 50.0
        assert any(item["path"] == "/users" for item in payload["uncovered"])

    def test_uses_active_profile_defaults(self, tmp_path):
        openapi_file = tmp_path / "openapi.yaml"
        openapi_file.write_text(
            "\n".join(
                [
                    "openapi: 3.0.0",
                    "info:",
                    "  title: Demo API",
                    "  version: 1.0.0",
                    "paths:",
                    "  /users:",
                    "    get:",
                    "      responses:",
                    "        '200':",
                    "          description: OK",
                ],
            ),
            encoding="utf-8",
        )
        junit_file = tmp_path / "reports" / "schemathesis" / "junit.xml"
        junit_file.parent.mkdir(parents=True, exist_ok=True)
        junit_file.write_text(
            "\n".join(
                [
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '<testsuite name="schemathesis" tests="1" failures="0" errors="0" skipped="0" time="0.1">',
                    '  <testcase classname="schemathesis" name="GET /users returns 200" time="0.1" />',
                    "</testsuite>",
                ],
            ),
            encoding="utf-8",
        )

        entry = MagicMock()
        entry.resolved_path.return_value = tmp_path
        profile = QAAgentProfile(
            project=ProjectSettings(name="demo", type="api"),
            openapi=OpenAPISettings(spec_path="openapi.yaml"),
        )

        with patch("qaagent.commands.analyze_cmd.load_active_profile", return_value=(entry, profile)):
            result = runner.invoke(app, ["analyze", "coverage-gaps"])

        assert result.exit_code == 0
        assert "Route Coverage Gaps" in result.output


class TestAnalyzeDom:
    def test_help(self):
        result = runner.invoke(app, ["analyze", "dom", "--help"])
        assert result.exit_code == 0

    def test_requires_url_or_active_profile(self):
        with patch("qaagent.commands.analyze_cmd.load_active_profile", side_effect=Exception("No active")):
            result = runner.invoke(app, ["analyze", "dom"])
        assert result.exit_code == 2
        assert "Provide --url" in result.output

    def test_explicit_url(self, tmp_path):
        out_file = tmp_path / "dom-analysis.json"
        analysis = {
            "summary": {
                "pages_analyzed": 1,
                "elements_total": 55,
                "interactive_elements": 12,
                "forms_total": 1,
                "selector_strategy": {
                    "stable_selector_coverage_pct": 75.0,
                    "testid_coverage_pct": 41.7,
                    "aria_coverage_pct": 58.3,
                },
            },
            "recommendations": ["Adopt data-testid attributes for critical interactive controls."],
        }

        with patch("qaagent.commands.analyze_cmd.run_dom_analysis", return_value=analysis) as mock_run:
            result = runner.invoke(
                app,
                ["analyze", "dom", "--url", "https://app.example.com", "--out", str(out_file)],
            )

        assert result.exit_code == 0
        assert "DOM analysis written" in result.output
        kwargs = mock_run.call_args.kwargs
        assert kwargs["url"] == "https://app.example.com"
        assert kwargs["out_path"] == out_file

    def test_uses_active_profile_for_base_url_and_auth(self, tmp_path):
        out_file = tmp_path / "dom-analysis.json"
        analysis = {
            "summary": {
                "pages_analyzed": 1,
                "elements_total": 10,
                "interactive_elements": 3,
                "forms_total": 0,
                "selector_strategy": {
                    "stable_selector_coverage_pct": 100.0,
                    "testid_coverage_pct": 66.7,
                    "aria_coverage_pct": 66.7,
                },
            },
            "recommendations": [],
        }

        entry = MagicMock()
        entry.resolved_path.return_value = tmp_path
        profile = QAAgentProfile(
            project=ProjectSettings(name="demo", type="web"),
            openapi=OpenAPISettings(),
            app={
                "dev": EnvironmentSettings(
                    base_url="https://secure.example.com",
                    headers={"X-Tenant": "acme"},
                    auth=AuthSettings(
                        header_name="Authorization",
                        token_env="API_TOKEN",
                        prefix="Bearer ",
                    ),
                )
            },
        )

        with patch("qaagent.commands.analyze_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.commands.analyze_cmd.run_dom_analysis", return_value=analysis) as mock_run:
            result = runner.invoke(app, ["analyze", "dom", "--out", str(out_file)], env={"API_TOKEN": "secret"})

        assert result.exit_code == 0
        kwargs = mock_run.call_args.kwargs
        assert kwargs["url"] == "https://secure.example.com"
        assert kwargs["headers"]["X-Tenant"] == "acme"
        assert kwargs["headers"]["Authorization"] == "Bearer secret"
