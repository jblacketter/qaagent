"""CLI split parity tests.

Verifies that the CLI command tree after splitting cli.py into command modules
matches the pre-split snapshot exactly. This ensures no commands were lost,
renamed, or accidentally added during the refactor.
"""
from __future__ import annotations

import json
from pathlib import Path

import click
import pytest
from typer.main import get_command
from typer.testing import CliRunner

from qaagent.commands import app

SNAPSHOT_PATH = Path(__file__).parent.parent / "fixtures" / "cli_snapshots" / "pre_split_commands.json"
runner = CliRunner()


@pytest.fixture
def snapshot():
    """Load the pre-split CLI command tree snapshot."""
    with open(SNAPSHOT_PATH) as f:
        return json.load(f)


def _get_command_tree():
    """Get the current CLI command tree using Typer/Click internals."""
    cmd = get_command(app)
    ctx = click.Context(cmd)
    commands = sorted(cmd.list_commands(ctx))

    subgroups = {}
    for name in commands:
        sub = cmd.get_command(ctx, name)
        if hasattr(sub, "list_commands"):
            sub_ctx = click.Context(sub, parent=ctx)
            subgroups[name] = sorted(sub.list_commands(sub_ctx))

    return {"top_level_commands": commands, "subgroups": subgroups}


class TestCommandParity:
    """Verify command names match the pre-split snapshot."""

    def test_top_level_commands_match(self, snapshot):
        current = _get_command_tree()
        assert current["top_level_commands"] == snapshot["top_level_commands"], (
            f"Top-level command mismatch.\n"
            f"Missing: {set(snapshot['top_level_commands']) - set(current['top_level_commands'])}\n"
            f"Extra: {set(current['top_level_commands']) - set(snapshot['top_level_commands'])}"
        )

    def test_analyze_subcommands_match(self, snapshot):
        current = _get_command_tree()
        assert current["subgroups"]["analyze"] == snapshot["subgroups"]["analyze"]

    def test_config_subcommands_match(self, snapshot):
        current = _get_command_tree()
        assert current["subgroups"]["config"] == snapshot["subgroups"]["config"]

    def test_targets_subcommands_match(self, snapshot):
        current = _get_command_tree()
        assert current["subgroups"]["targets"] == snapshot["subgroups"]["targets"]

    def test_generate_subcommands_match(self, snapshot):
        current = _get_command_tree()
        assert current["subgroups"]["generate"] == snapshot["subgroups"]["generate"]

    def test_workspace_subcommands_match(self, snapshot):
        current = _get_command_tree()
        assert current["subgroups"]["workspace"] == snapshot["subgroups"]["workspace"]

    def test_all_subgroups_present(self, snapshot):
        current = _get_command_tree()
        assert set(current["subgroups"].keys()) == set(snapshot["subgroups"].keys()), (
            f"Subgroup mismatch.\n"
            f"Missing: {set(snapshot['subgroups'].keys()) - set(current['subgroups'].keys())}\n"
            f"Extra: {set(current['subgroups'].keys()) - set(snapshot['subgroups'].keys())}"
        )


class TestHelpExitCodes:
    """Smoke tests: each command group's --help exits 0."""

    def test_main_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_analyze_help(self):
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0

    def test_analyze_routes_help(self):
        result = runner.invoke(app, ["analyze", "routes", "--help"])
        assert result.exit_code == 0

    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0

    def test_config_init_help(self):
        result = runner.invoke(app, ["config", "init", "--help"])
        assert result.exit_code == 0

    def test_targets_help(self):
        result = runner.invoke(app, ["targets", "--help"])
        assert result.exit_code == 0

    def test_generate_help(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0

    def test_generate_behave_help(self):
        result = runner.invoke(app, ["generate", "behave", "--help"])
        assert result.exit_code == 0

    def test_workspace_help(self):
        result = runner.invoke(app, ["workspace", "--help"])
        assert result.exit_code == 0

    def test_schemathesis_run_help(self):
        result = runner.invoke(app, ["schemathesis-run", "--help"])
        assert result.exit_code == 0

    def test_doctor_help(self):
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0

    def test_version_exits_zero(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "qaagent" in result.output


class TestAnalyzeInvocation:
    """Verify that analyze command variants all work (codex review feedback)."""

    def test_analyze_no_args_exits_zero(self):
        result = runner.invoke(app, ["analyze"])
        assert result.exit_code == 0
        assert "QA Analysis" in result.output

    def test_analyze_dot_exits_zero(self):
        result = runner.invoke(app, ["analyze", "."])
        assert result.exit_code == 0
        assert "QA Analysis" in result.output

    def test_analyze_repo_dot_exits_zero(self):
        result = runner.invoke(app, ["analyze", "repo", "."])
        assert result.exit_code == 0
        assert "QA Analysis" in result.output

    def test_analyze_routes_help_exits_zero(self):
        result = runner.invoke(app, ["analyze", "routes", "--help"])
        assert result.exit_code == 0
        assert "routes" in result.output.lower()


class TestTargetsListSmoke:
    """Smoke test for targets list (exits 0 even with empty registry)."""

    def test_targets_list_exits_zero(self):
        result = runner.invoke(app, ["targets", "list"])
        assert result.exit_code == 0
