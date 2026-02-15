"""Integration tests for workspace CLI commands."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qaagent.commands import app

runner = CliRunner()


def _mock_active_profile(name="myapp", path="/tmp/myapp"):
    entry = MagicMock()
    entry.name = name
    entry.resolved_path.return_value = Path(path)
    profile = MagicMock()
    return entry, profile


class TestWorkspaceShow:
    def test_show_existing_workspace(self):
        entry, profile = _mock_active_profile()
        ws = MagicMock()
        ws.get_workspace_info.return_value = {
            "exists": True,
            "path": "/home/.qaagent/workspace/myapp",
            "files": {"openapi.json": {"size": 2048}},
        }
        with patch("qaagent.commands.workspace_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "show"])
        assert result.exit_code == 0
        assert "myapp" in result.output

    def test_show_no_workspace(self):
        entry, profile = _mock_active_profile()
        ws = MagicMock()
        ws.get_workspace_info.return_value = {"exists": False, "path": "/tmp", "files": {}}
        with patch("qaagent.commands.workspace_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "show"])
        assert result.exit_code == 0
        assert "No workspace" in result.output

    def test_show_no_active_target(self):
        with patch("qaagent.commands.workspace_cmd.load_active_profile", side_effect=Exception("No active")):
            result = runner.invoke(app, ["workspace", "show"])
        assert result.exit_code == 2

    def test_show_explicit_target(self):
        ws = MagicMock()
        ws.get_workspace_info.return_value = {
            "exists": True,
            "path": "/home/.qaagent/workspace/demo",
            "files": {},
        }
        with patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "show", "demo"])
        assert result.exit_code == 0
        assert "demo" in result.output


class TestWorkspaceList:
    def test_list_with_targets(self):
        ws = MagicMock()
        ws.list_targets.return_value = ["myapp", "demo"]
        ws.get_workspace_info.return_value = {"files": {"tests": {"unit": 2}}}
        with patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "list"])
        assert result.exit_code == 0
        assert "2 targets" in result.output

    def test_list_empty(self):
        ws = MagicMock()
        ws.list_targets.return_value = []
        with patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "list"])
        assert result.exit_code == 0
        assert "No workspaces" in result.output


class TestWorkspaceClean:
    def test_clean_all_force(self):
        ws = MagicMock()
        with patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "clean", "--all", "--force"])
        assert result.exit_code == 0
        ws.clean_all.assert_called_once()

    def test_clean_target_force(self):
        entry, profile = _mock_active_profile()
        ws = MagicMock()
        with patch("qaagent.commands.workspace_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "clean", "--force"])
        assert result.exit_code == 0
        ws.clean_target.assert_called_once_with("myapp")

    def test_clean_no_target_no_all(self):
        with patch("qaagent.commands.workspace_cmd.load_active_profile", side_effect=Exception("No active")):
            result = runner.invoke(app, ["workspace", "clean", "--force"])
        assert result.exit_code == 2


class TestWorkspaceApply:
    def test_apply_copies_files(self):
        entry, profile = _mock_active_profile()
        ws = MagicMock()
        src = Path("/ws/openapi.json")
        dest = Path("/tmp/myapp/openapi.json")
        ws.copy_to_target.return_value = [(src, dest)]
        with patch("qaagent.commands.workspace_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "apply"])
        assert result.exit_code == 0
        assert "Copied 1 files" in result.output

    def test_apply_no_matching_files(self):
        entry, profile = _mock_active_profile()
        ws = MagicMock()
        ws.copy_to_target.return_value = []
        with patch("qaagent.commands.workspace_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "apply"])
        assert result.exit_code == 0
        assert "No files" in result.output

    def test_apply_dry_run(self):
        entry, profile = _mock_active_profile()
        ws = MagicMock()
        src = Path("/ws/openapi.json")
        dest = Path("/tmp/myapp/openapi.json")
        ws.copy_to_target.return_value = [(src, dest)]
        with patch("qaagent.commands.workspace_cmd.load_active_profile", return_value=(entry, profile)), \
             patch("qaagent.workspace.Workspace", return_value=ws):
            result = runner.invoke(app, ["workspace", "apply", "--dry-run"])
        assert result.exit_code == 0
        assert "Would copy" in result.output
