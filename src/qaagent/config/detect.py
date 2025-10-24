from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def detect_project_type(project_path: Path) -> str:
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = {*(data.get("dependencies") or {}), *(data.get("devDependencies") or {})}
            deps = {name.lower() for name in deps}
            if any(name.startswith("next") for name in deps):
                return "nextjs"
        except Exception:
            pass

    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        contents = pyproject.read_text(encoding="utf-8").lower()
        if "fastapi" in contents:
            return "fastapi"

    requirements = project_path / "requirements.txt"
    if requirements.exists():
        contents = requirements.read_text(encoding="utf-8").lower()
        if "fastapi" in contents:
            return "fastapi"

    return "generic"


def default_base_url(project_type: str) -> str:
    if project_type == "nextjs":
        return "http://localhost:3000"
    if project_type == "fastapi":
        return "http://localhost:8765"
    return "http://localhost:8000"


def default_start_command(project_type: str) -> Optional[str]:
    if project_type == "nextjs":
        return "npm run dev"
    if project_type == "fastapi":
        return "uvicorn server:app --reload --port 8765"
    return None


def default_spec_path(project_type: str) -> str:
    if project_type == "nextjs":
        return ".qaagent/openapi.yaml"
    return "openapi.yaml"


def default_source_dir(project_type: str) -> Optional[str]:
    if project_type == "nextjs":
        return "src/app/api"
    return None
