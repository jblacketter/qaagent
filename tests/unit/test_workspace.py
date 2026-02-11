"""Tests for Workspace class."""
from __future__ import annotations

from pathlib import Path

from qaagent.workspace import Workspace


class TestWorkspaceInit:
    def test_default_base_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        ws = Workspace()
        assert ws.base_dir == tmp_path / ".qaagent" / "workspace"
        assert ws.base_dir.is_dir()

    def test_custom_base_dir(self, tmp_path):
        base = tmp_path / "custom"
        ws = Workspace(base_dir=base)
        assert ws.base_dir == base
        assert base.is_dir()


class TestWorkspaceTargets:
    def test_get_target_workspace(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        target_dir = ws.get_target_workspace("myapp")
        assert target_dir == tmp_path / "myapp"
        assert target_dir.is_dir()

    def test_list_targets_empty(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        assert ws.list_targets() == []

    def test_list_targets(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        (tmp_path / "app1").mkdir()
        (tmp_path / "app2").mkdir()
        targets = ws.list_targets()
        assert set(targets) == {"app1", "app2"}

    def test_list_targets_ignores_files(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        (tmp_path / "app1").mkdir()
        (tmp_path / "stray_file.txt").write_text("x")
        assert ws.list_targets() == ["app1"]


class TestWorkspacePaths:
    def test_get_openapi_path_json(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        path = ws.get_openapi_path("myapp", format="json")
        assert path == tmp_path / "myapp" / "openapi.json"

    def test_get_openapi_path_yaml(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        path = ws.get_openapi_path("myapp", format="yaml")
        assert path == tmp_path / "myapp" / "openapi.yaml"

    def test_get_tests_dir(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        tests_dir = ws.get_tests_dir("myapp", test_type="behave")
        assert tests_dir == tmp_path / "myapp" / "tests" / "behave"
        assert tests_dir.is_dir()

    def test_get_reports_dir(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        reports_dir = ws.get_reports_dir("myapp")
        assert reports_dir == tmp_path / "myapp" / "reports"
        assert reports_dir.is_dir()

    def test_get_fixtures_dir(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        fixtures_dir = ws.get_fixtures_dir("myapp")
        assert fixtures_dir == tmp_path / "myapp" / "fixtures"
        assert fixtures_dir.is_dir()


class TestWorkspaceClean:
    def test_clean_target(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        target_dir = ws.get_target_workspace("myapp")
        (target_dir / "file.txt").write_text("data")

        ws.clean_target("myapp")

        assert not target_dir.exists()

    def test_clean_target_nonexistent(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        ws.clean_target("nonexistent")  # Should not raise

    def test_clean_all(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        ws.get_target_workspace("app1")
        ws.get_target_workspace("app2")

        ws.clean_all()

        assert ws.base_dir.is_dir()
        assert ws.list_targets() == []


class TestWorkspaceInfo:
    def test_info_nonexistent(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        info = ws.get_workspace_info("nonexistent")
        assert info["exists"] is False

    def test_info_empty_workspace(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        ws.get_target_workspace("myapp")
        info = ws.get_workspace_info("myapp")

        assert info["exists"] is True
        assert "path" in info

    def test_info_with_openapi(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        ws.get_target_workspace("myapp")
        (tmp_path / "myapp" / "openapi.json").write_text('{"openapi":"3.0.0"}')

        info = ws.get_workspace_info("myapp")

        assert "openapi.json" in info["files"]
        assert info["files"]["openapi.json"]["size"] > 0

    def test_info_with_tests(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        tests_dir = ws.get_tests_dir("myapp", "unit")
        (tests_dir / "test_foo.py").write_text("pass")

        info = ws.get_workspace_info("myapp")

        assert info["files"]["tests"]["unit"] == 1

    def test_info_with_reports(self, tmp_path):
        ws = Workspace(base_dir=tmp_path)
        reports_dir = ws.get_reports_dir("myapp")
        (reports_dir / "report.html").write_text("<html/>")

        info = ws.get_workspace_info("myapp")

        assert info["files"]["reports"] == 1


class TestWorkspaceCopyToTarget:
    def test_copy_files(self, tmp_path):
        ws = Workspace(base_dir=tmp_path / "workspace")
        target_ws = ws.get_target_workspace("myapp")
        (target_ws / "config.json").write_text('{"key":"val"}')

        dest = tmp_path / "project"
        dest.mkdir()

        copied = ws.copy_to_target("myapp", dest)

        assert len(copied) == 1
        assert (dest / "config.json").exists()
        assert (dest / "config.json").read_text() == '{"key":"val"}'

    def test_copy_nested_files(self, tmp_path):
        ws = Workspace(base_dir=tmp_path / "workspace")
        tests_dir = ws.get_tests_dir("myapp", "unit")
        (tests_dir / "test_a.py").write_text("pass")

        dest = tmp_path / "project"
        dest.mkdir()

        copied = ws.copy_to_target("myapp", dest)

        assert (dest / "tests" / "unit" / "test_a.py").exists()

    def test_copy_dry_run(self, tmp_path):
        ws = Workspace(base_dir=tmp_path / "workspace")
        target_ws = ws.get_target_workspace("myapp")
        (target_ws / "file.txt").write_text("data")

        dest = tmp_path / "project"
        dest.mkdir()

        copied = ws.copy_to_target("myapp", dest, dry_run=True)

        assert len(copied) == 1
        assert not (dest / "file.txt").exists()
