from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "qaagent", *args]
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=180.0)


def test_generate_behave_creates_feature(tmp_path: Path) -> None:
    qa_home = tmp_path / ".qaagent-home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Minimal FastAPI-like project with OpenAPI spec
    openapi_path = project_dir / "openapi.yaml"
    openapi_path.write_text(
        """
openapi: 3.0.3
info:
  title: Demo API
  version: '1.0'
paths:
  /items:
    get:
      responses:
        '200':
          description: OK
    post:
      responses:
        '201':
          description: Created
"""
    ,
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["QAAGENT_HOME"] = str(qa_home)
    pythonpath_parts = [str(Path.cwd() / "src")]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    init_result = _run_cli(
        [
            "config",
            "init",
            str(project_dir),
            "--template",
            "fastapi",
            "--name",
            "demo",
            "--register",
            "--activate",
        ],
        cwd=project_dir,
        env=env,
    )
    assert init_result.returncode == 0, init_result.stderr

    gen_result = _run_cli([
        "generate",
        "behave",
        "--out",
        "tests/generated/behave",
    ], cwd=project_dir, env=env)
    assert gen_result.returncode == 0, gen_result.stderr

    feature_path = project_dir / "tests" / "generated" / "behave" / "features" / "items.feature"
    assert feature_path.exists()
    text = feature_path.read_text(encoding="utf-8")
    assert "Feature:" in text
    assert "Scenario:" in text
