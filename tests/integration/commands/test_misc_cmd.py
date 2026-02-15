"""Integration tests for miscellaneous CLI commands."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qaagent.commands import app
from qaagent.doctor import HealthCheck, HealthStatus

runner = CliRunner()


class TestDoctor:
    def test_help(self):
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0

    def test_all_ok(self):
        checks = [
            HealthCheck(name="Python", status=HealthStatus.OK, message="3.11.5"),
            HealthCheck(name="Node.js", status=HealthStatus.OK, message="v20.0.0"),
        ]
        with patch("qaagent.commands.misc_cmd.run_health_checks", return_value=checks):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output

    def test_with_errors(self):
        checks = [
            HealthCheck(name="Python", status=HealthStatus.OK, message="3.11.5"),
            HealthCheck(name="Missing", status=HealthStatus.ERROR, message="Not found", suggestion="Install it"),
        ]
        with patch("qaagent.commands.misc_cmd.run_health_checks", return_value=checks):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "failing" in result.output

    def test_json_output(self):
        checks = [
            HealthCheck(name="Python", status=HealthStatus.OK, message="3.11.5"),
        ]
        with patch("qaagent.commands.misc_cmd.run_health_checks", return_value=checks):
            result = runner.invoke(app, ["doctor", "--json-out"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "checks" in data
        assert "platform" in data

    def test_warnings_only(self):
        checks = [
            HealthCheck(name="Python", status=HealthStatus.OK, message="3.11.5"),
            HealthCheck(name="Optional", status=HealthStatus.WARNING, message="Missing", suggestion="Install"),
        ]
        with patch("qaagent.commands.misc_cmd.run_health_checks", return_value=checks):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "warning" in result.output.lower()


class TestFixIssues:
    def test_help(self):
        result = runner.invoke(app, ["fix", "--help"])
        assert result.exit_code == 0

    def test_no_active_target(self):
        with patch("qaagent.commands.misc_cmd.load_active_profile", side_effect=Exception("No active")):
            result = runner.invoke(app, ["fix"])
        assert result.exit_code == 2

    def test_success_autopep8(self):
        entry = MagicMock()
        entry.name = "myapp"
        entry.resolved_path.return_value = Path("/tmp/myapp")
        profile = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.files_modified = 3
        mock_result.message = "Fixed 3 files"
        mock_result.errors = []
        with patch("qaagent.commands.misc_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.autofix.AutoFixer.fix_formatting", return_value=mock_result):
            result = runner.invoke(app, ["fix", "--tool", "autopep8"])
        assert result.exit_code == 0
        assert "Fixes applied" in result.output

    def test_unknown_tool(self):
        entry = MagicMock()
        entry.name = "myapp"
        entry.resolved_path.return_value = Path("/tmp/myapp")
        profile = MagicMock()
        with patch("qaagent.commands.misc_cmd.load_active_profile", return_value=(entry, profile)):
            result = runner.invoke(app, ["fix", "--tool", "unknown_tool"])
        assert result.exit_code == 1
        assert "Unknown tool" in result.output


class TestVersion:
    def test_outputs_json(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "qaagent" in data
        assert "python" in data


class TestInit:
    def test_creates_config(self):
        with patch("qaagent.commands.misc_cmd.write_default_config", return_value=Path(".qaagent.toml")), \
             patch("qaagent.commands.misc_cmd.write_env_example", return_value=Path(".env.example")):
            result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "Wrote" in result.output


class TestApiDetect:
    def test_help(self):
        result = runner.invoke(app, ["api-detect", "--help"])
        assert result.exit_code == 0

    def test_no_files_found(self, tmp_path):
        with patch("qaagent.commands.misc_cmd.find_openapi_candidates", return_value=[]):
            result = runner.invoke(app, ["api-detect", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "none found" in result.output

    def test_files_found(self, tmp_path):
        spec = tmp_path / "openapi.yaml"
        spec.write_text("openapi: 3.0.0")
        with patch("qaagent.commands.misc_cmd.find_openapi_candidates", return_value=[spec]), \
             patch("qaagent.commands.misc_cmd.load_openapi", return_value={}), \
             patch("qaagent.commands.misc_cmd.enumerate_operations", return_value=[MagicMock(), MagicMock()]):
            result = runner.invoke(app, ["api-detect", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "2" in result.output


class TestGenTests:
    def test_help(self):
        result = runner.invoke(app, ["gen-tests", "--help"])
        assert result.exit_code == 0

    def test_unsupported_kind(self):
        result = runner.invoke(app, ["gen-tests", "--kind", "ui"])
        assert result.exit_code == 2

    def test_no_spec(self):
        with patch("qaagent.commands.misc_cmd.load_config_compat", return_value=None), \
             patch("qaagent.commands.misc_cmd.find_openapi_candidates", return_value=[]):
            result = runner.invoke(app, ["gen-tests"])
        assert result.exit_code == 2
        assert "not provided" in result.output

    def test_dry_run(self, tmp_path):
        spec = tmp_path / "openapi.json"
        spec.write_text("{}")
        with patch("qaagent.commands.misc_cmd.load_config_compat", return_value=None), \
             patch("qaagent.commands.misc_cmd.load_openapi", return_value={}), \
             patch("qaagent.commands.misc_cmd.generate_api_tests_from_spec", return_value="def test_api(): pass"):
            result = runner.invoke(app, [
                "gen-tests", "--openapi", str(spec),
                "--base-url", "http://localhost:8000", "--dry-run",
            ])
        assert result.exit_code == 0
        assert "def test_api" in result.output

    def test_use_rag_missing_index_exits_2(self, tmp_path):
        spec = tmp_path / "openapi.json"
        spec.write_text("{}")

        with patch("qaagent.commands.misc_cmd.load_config_compat", return_value=None), \
             patch("qaagent.commands.misc_cmd.load_openapi", return_value={}):
            result = runner.invoke(app, ["gen-tests", "--openapi", str(spec), "--use-rag"])

        assert result.exit_code == 2
        assert "RAG index not found" in result.output

    def test_use_rag_passes_retrieval_context(self, tmp_path):
        spec = tmp_path / "openapi.json"
        spec.write_text("{}")

        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "chunks": [
                        {
                            "chunk_id": "docs/api.md:1",
                            "path": "docs/api.md",
                            "text": "POST /pets requires name and species fields",
                            "start_line": 1,
                            "end_line": 1,
                        }
                    ],
                }
            )
        )

        op = SimpleNamespace(method="POST", path="/pets")
        with patch("qaagent.commands.misc_cmd.load_config_compat", return_value=None), \
             patch("qaagent.commands.misc_cmd.load_openapi", return_value={}), \
             patch("qaagent.commands.misc_cmd.enumerate_operations", return_value=[op]), \
             patch("qaagent.commands.misc_cmd.generate_api_tests_from_spec", return_value="def test_api(): pass") as mock_generate:
            result = runner.invoke(
                app,
                [
                    "gen-tests",
                    "--openapi",
                    str(spec),
                    "--use-rag",
                    "--rag-index",
                    str(index_path),
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        kwargs = mock_generate.call_args.kwargs
        assert kwargs["retrieval_context"]
        assert "docs/api.md:1-1" in kwargs["retrieval_context"][0]


class TestWebUi:
    def test_help(self):
        result = runner.invoke(app, ["web-ui", "--help"])
        assert result.exit_code == 0


class TestApi:
    def test_help(self):
        result = runner.invoke(app, ["api", "--help"])
        assert result.exit_code == 0


class TestMcpStdio:
    def test_help(self):
        result = runner.invoke(app, ["mcp-stdio", "--help"])
        assert result.exit_code == 0
