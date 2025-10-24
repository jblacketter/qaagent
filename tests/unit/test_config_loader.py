from __future__ import annotations

import os
from pathlib import Path

import pytest

from qaagent.config.loader import CONFIG_FILENAME, find_config_file, load_profile


def _write_basic_config(path: Path, project_name: str = "Example") -> Path:
    content = (
        "project:\n"
        f"  name: \"{project_name}\"\n"
        "app:\n"
        "  dev:\n"
        "    base_url: \"http://localhost:8000\"\n"
    )
    config_path = path / CONFIG_FILENAME
    config_path.write_text(content, encoding="utf-8")
    return config_path


def test_find_config_file_walks_up(tmp_path: Path) -> None:
    project = tmp_path / "project"
    subdir = project / "src"
    subdir.mkdir(parents=True)
    config_path = _write_basic_config(project)

    found = find_config_file(subdir)
    assert found == config_path


def test_load_profile_parses_yaml(tmp_path: Path) -> None:
    config_path = _write_basic_config(tmp_path, project_name="SonicGrid")

    profile = load_profile(config_path)

    assert profile.project.name == "SonicGrid"
    assert "dev" in profile.app
    assert profile.tests.behave.output_dir == "tests/qaagent/behave"
