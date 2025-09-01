from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Optional


@dataclass
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    tail: int = 5000,
    env: Optional[dict] = None,
) -> CmdResult:
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=proc_env,
    )
    stdout = proc.stdout[-tail:] if proc.stdout else ""
    stderr = proc.stderr[-tail:] if proc.stderr else ""
    return CmdResult(proc.returncode, stdout, stderr)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
