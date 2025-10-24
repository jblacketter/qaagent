from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "qaagent", *args]
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=120.0)


def test_analyze_routes_cli_generates_output(project_root: Path, tmp_path: Path) -> None:
    openapi_path = project_root / "examples" / "petstore-api" / "openapi.yaml"
    out_file = tmp_path / "routes.json"
    result = _run_cli([
        "analyze",
        "routes",
        "--openapi",
        str(openapi_path),
        "--out",
        str(out_file),
    ], project_root)
    assert result.returncode == 0, result.stderr
    data = json.loads(out_file.read_text())
    assert isinstance(data, list) and data


def test_analyze_risks_cli_runs(project_root: Path, tmp_path: Path) -> None:
    openapi_path = project_root / "examples" / "petstore-api" / "openapi.yaml"
    routes_out = tmp_path / "routes.json"
    risks_out = tmp_path / "risks.json"

    # Generate routes first
    result_routes = _run_cli([
        "analyze",
        "routes",
        "--openapi",
        str(openapi_path),
        "--out",
        str(routes_out),
    ], project_root)
    assert result_routes.returncode == 0, result_routes.stderr

    result_risks = _run_cli([
        "analyze",
        "risks",
        "--routes",
        str(routes_out),
        "--out",
        str(risks_out),
        "--markdown",
        str(tmp_path / "risks.md"),
    ], project_root)
    assert result_risks.returncode == 0, result_risks.stderr
    data = json.loads(risks_out.read_text())
    assert isinstance(data, list)
