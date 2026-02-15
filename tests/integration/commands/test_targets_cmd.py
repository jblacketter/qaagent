"""Integration tests for targets CLI commands."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qaagent.commands import app

runner = CliRunner()


class TestTargetsList:
    def test_empty_registry(self):
        mock_manager = MagicMock()
        mock_manager.list_targets.return_value = []
        mock_manager.registry.active = None
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager):
            result = runner.invoke(app, ["targets", "list"])
        assert result.exit_code == 0
        assert "No targets" in result.output

    def test_with_targets(self):
        entry = MagicMock()
        entry.name = "myapp"
        entry.path = "/tmp/myapp"
        entry.project_type = "fastapi"
        mock_manager = MagicMock()
        mock_manager.list_targets.return_value = [entry]
        mock_manager.registry.active = "myapp"
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager):
            result = runner.invoke(app, ["targets", "list"])
        assert result.exit_code == 0


class TestTargetsAdd:
    def test_add_success(self, tmp_path):
        project = tmp_path / "myapp"
        project.mkdir()
        mock_manager = MagicMock()
        mock_entry = MagicMock()
        mock_entry.name = "myapp"
        mock_manager.add_target.return_value = mock_entry
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager), \
             patch("qaagent.commands.targets_cmd.detect_project_type", return_value="generic"):
            result = runner.invoke(app, ["targets", "add", "myapp", str(project)])
        assert result.exit_code == 0
        assert "Registered" in result.output

    def test_add_with_activate(self, tmp_path):
        project = tmp_path / "myapp"
        project.mkdir()
        mock_manager = MagicMock()
        mock_entry = MagicMock()
        mock_entry.name = "myapp"
        mock_manager.add_target.return_value = mock_entry
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager), \
             patch("qaagent.commands.targets_cmd.detect_project_type", return_value="generic"):
            result = runner.invoke(app, ["targets", "add", "myapp", str(project), "--activate"])
        assert result.exit_code == 0
        assert "Activated" in result.output
        mock_manager.set_active.assert_called_once_with("myapp")

    def test_add_value_error(self, tmp_path):
        project = tmp_path / "myapp"
        project.mkdir()
        mock_manager = MagicMock()
        mock_manager.add_target.side_effect = ValueError("Already exists")
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager), \
             patch("qaagent.commands.targets_cmd.detect_project_type", return_value="generic"):
            result = runner.invoke(app, ["targets", "add", "myapp", str(project)])
        assert result.exit_code == 1


class TestTargetsRemove:
    def test_remove_success(self):
        mock_manager = MagicMock()
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager):
            result = runner.invoke(app, ["targets", "remove", "myapp"])
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_remove_nonexistent(self):
        mock_manager = MagicMock()
        mock_manager.remove_target.side_effect = ValueError("Not found")
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager):
            result = runner.invoke(app, ["targets", "remove", "nosuch"])
        assert result.exit_code == 1


class TestUseTarget:
    def test_use_success(self):
        entry = MagicMock()
        entry.name = "myapp"
        entry.path = "/tmp/myapp"
        mock_manager = MagicMock()
        mock_manager.set_active.return_value = entry
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager):
            result = runner.invoke(app, ["use", "myapp"])
        assert result.exit_code == 0
        assert "Active target" in result.output

    def test_use_nonexistent(self):
        mock_manager = MagicMock()
        mock_manager.set_active.side_effect = ValueError("Not found")
        with patch("qaagent.commands.targets_cmd.target_manager", return_value=mock_manager):
            result = runner.invoke(app, ["use", "nosuch"])
        assert result.exit_code == 1
