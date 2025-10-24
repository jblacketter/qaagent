from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "qaagent", *args]
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=60.0)


def test_doctor_json_output(project_root: Path, cli_env: dict[str, str]) -> None:
    result = _run_cli(["doctor", "--json-out"], cwd=project_root, env=cli_env)
    assert result.returncode in (0, 1), result.stderr
    payload = json.loads(result.stdout)
    assert "checks" in payload and isinstance(payload["checks"], list)
    names = {check["name"] for check in payload["checks"]}
    assert "Python" in names
    assert "MCP server" in names
