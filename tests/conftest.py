from __future__ import annotations

import os
import socket
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


def _find_free_port() -> int:
    """Bind to port 0 to let the OS assign a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_http(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if 200 <= response.status < 500:
                    return
        except Exception:
            pass
        time.sleep(0.3)
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
    port = _find_free_port()
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    url = f"http://{host}:{port}"
    try:
        _wait_for_http(f"{url}/health", timeout=15.0)
        yield url
    except RuntimeError:
        # Kill process first, then safely read stderr (avoids blocking
        # on a read if the process is still alive and hasn't flushed).
        proc.kill()
        try:
            _, stderr_bytes = proc.communicate(timeout=5.0)
            stderr_tail = stderr_bytes.decode("utf-8", errors="replace")[:4096]
        except Exception:
            stderr_tail = ""
        raise RuntimeError(
            f"Petstore server failed to start on {url}.\n"
            f"Stderr: {stderr_tail or '(empty)'}"
        )
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
