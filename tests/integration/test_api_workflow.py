from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


pytest.importorskip("schemathesis")


def _run_cli(args: list[str], *, cwd: Path, env: dict[str, str], timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "qaagent", *args]
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_full_api_workflow(petstore_server: str, project_root: Path, tmp_path: Path, cli_env: dict[str, str]) -> None:
    env = cli_env.copy()
    env["QAAGENT_CONFIG"] = str(project_root / "examples" / "petstore-api" / ".qaagent.toml")
    env.setdefault("BASE_URL", petstore_server)

    analyze = _run_cli(["analyze", "examples/petstore-api"], cwd=project_root, env=env)
    assert analyze.returncode == 0, analyze.stderr

    reports_dir = tmp_path / "schemathesis"
    schemathesis = _run_cli(
        [
            "schemathesis-run",
            "--openapi",
            str(project_root / "examples" / "petstore-api" / "openapi.yaml"),
            "--base-url",
            petstore_server,
            "--outdir",
            str(reports_dir),
        ],
        cwd=project_root,
        env=env,
        timeout=180.0,
    )
    assert schemathesis.returncode == 0, schemathesis.stderr
    junit = reports_dir / "junit.xml"
    assert junit.exists(), f"Expected Schemathesis JUnit output at {junit}"

    findings = tmp_path / "findings.md"
    report = _run_cli(
        [
            "report",
            "--sources",
            str(junit),
            "--out",
            str(findings),
        ],
        cwd=project_root,
        env=env,
    )
    assert report.returncode == 0, report.stderr
    assert findings.exists()

    # Report command prints JSON when requested; ensure CLI can emit metadata
    report_json = _run_cli(
        [
            "report",
            "--sources",
            str(junit),
            "--out",
            str(findings),
            "--json-out",
        ],
        cwd=project_root,
        env=env,
    )
    assert report_json.returncode == 0, report_json.stderr
    payload = json.loads(report_json.stdout)
    assert payload["output"] == str(findings)
