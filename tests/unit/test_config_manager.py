from __future__ import annotations

from pathlib import Path

import pytest

from qaagent.config.loader import CONFIG_FILENAME
from qaagent.config.manager import TargetManager


def _write_basic_config(path: Path) -> None:
    content = (
        "project:\n"
        "  name: \"Sample\"\n"
        "app:\n"
        "  dev:\n"
        "    base_url: \"http://localhost:8000\"\n"
    )
    (path / CONFIG_FILENAME).write_text(content, encoding="utf-8")


def test_target_manager_add_list_remove(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QAAGENT_HOME", str(tmp_path / ".qaagent-home"))
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_basic_config(project_dir)

    manager = TargetManager()
    entry = manager.add_target("project", str(project_dir))
    assert entry.name == "project"
    assert manager.get("project") is not None

    manager.set_active("project")
    assert manager.get_active() is not None

    manager.remove_target("project")
    assert manager.get_active() is None
    assert manager.get("project") is None
