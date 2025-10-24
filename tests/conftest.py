from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Iterator

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _root() -> Path:
    # tests/conftest.py sits at repo/tests/, so parent is project root
    return PROJECT_ROOT


def _wait_for_http(url: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if 200 <= response.status < 500:
                    return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}")


@pytest.fixture(scope="session")
def project_root() -> Path:
    return _root()


@pytest.fixture(scope="session")
def petstore_server(project_root: Path) -> Iterator[str]:
    """Start the FastAPI petstore server for integration tests."""
    pytest.importorskip("uvicorn")
    pytest.importorskip("fastapi")
    host = "127.0.0.1"
    port = 8765
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "server:app",
        "--app-dir",
        str(project_root / "examples" / "petstore-api"),
        "--host",
        host,
        "--port",
        str(port),
    ]
    env = os.environ.copy()
    env.setdefault("UVICORN_LOG_LEVEL", "warning")
    proc = subprocess.Popen(
        cmd,
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    try:
        _wait_for_http(f"http://{host}:{port}/health", timeout=10.0)
        yield f"http://{host}:{port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture()
def cli_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("SCHEMATHESIS_MAX_EXAMPLES", "1")
    env.setdefault("PYTHONPATH", str(project_root))
    return env
