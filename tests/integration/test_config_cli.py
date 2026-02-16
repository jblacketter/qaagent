from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "qaagent", *args]
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=120.0)


def test_config_init_and_use(tmp_path: Path) -> None:
    qa_home = tmp_path / ".qaagent-home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    # Minimal project structure
    (project_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    env = os.environ.copy()
    env["QAAGENT_HOME"] = str(qa_home)
    pythonpath_parts = [str(Path.cwd() / "src")]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    result = _run_cli(
        [
            "config",
            "init",
            str(project_dir),
            "--template",
            "fastapi",
            "--name",
            "sample",
            "--register",
            "--activate",
        ],
        cwd=project_dir,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert (project_dir / ".qaagent.yaml").exists()

    list_result = _run_cli(["targets", "list"], cwd=project_dir, env=env)
    assert "sample" in list_result.stdout
    assert "*" in list_result.stdout  # active indicator

    use_result = _run_cli(["use", "sample"], cwd=project_dir, env=env)
    assert use_result.returncode == 0
