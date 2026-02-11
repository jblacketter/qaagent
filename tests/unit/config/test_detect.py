"""Tests for config/detect.py — project type detection heuristics."""
from __future__ import annotations

import json
from pathlib import Path

from qaagent.config.detect import (
    detect_project_type,
    default_base_url,
    default_start_command,
    default_spec_path,
    default_source_dir,
)


class TestDetectProjectType:
    def test_nextjs_from_package_json(self, tmp_path: Path):
        pkg = {"dependencies": {"next": "14.0.0", "react": "18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        assert detect_project_type(tmp_path) == "nextjs"

    def test_nextjs_from_dev_dependencies(self, tmp_path: Path):
        pkg = {"devDependencies": {"next": "14.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        assert detect_project_type(tmp_path) == "nextjs"

    def test_fastapi_from_pyproject(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi"]\n')

        assert detect_project_type(tmp_path) == "fastapi"

    def test_fastapi_from_requirements(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn\n")

        assert detect_project_type(tmp_path) == "fastapi"

    def test_generic_fallback(self, tmp_path: Path):
        assert detect_project_type(tmp_path) == "generic"

    def test_generic_when_package_json_has_no_next(self, tmp_path: Path):
        pkg = {"dependencies": {"express": "4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        assert detect_project_type(tmp_path) == "generic"

    def test_invalid_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text("not json")

        assert detect_project_type(tmp_path) == "generic"


class TestDefaults:
    def test_base_url_nextjs(self):
        assert default_base_url("nextjs") == "http://localhost:3000"

    def test_base_url_fastapi(self):
        assert default_base_url("fastapi") == "http://localhost:8765"

    def test_base_url_generic(self):
        assert default_base_url("generic") == "http://localhost:8000"

    def test_start_command_nextjs(self):
        assert default_start_command("nextjs") == "npm run dev"

    def test_start_command_fastapi(self):
        assert "uvicorn" in default_start_command("fastapi")

    def test_start_command_generic(self):
        assert default_start_command("generic") is None

    def test_spec_path_nextjs(self):
        assert default_spec_path("nextjs") == ".qaagent/openapi.yaml"

    def test_spec_path_generic(self):
        assert default_spec_path("generic") == "openapi.yaml"

    def test_source_dir_nextjs(self):
        assert default_source_dir("nextjs") == "src/app/api"

    def test_source_dir_generic(self):
        assert default_source_dir("generic") is None
