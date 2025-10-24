from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, List


class HealthStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str
    suggestion: str | None = None


OPTIONAL_FEATURES: tuple[tuple[str, str, str], ...] = (
    ("Schemathesis", "schemathesis", "pip install -e .[api]"),
    ("FastMCP", "mcp.server.fastmcp", "pip install -e .[mcp]"),
    ("Playwright", "playwright.sync_api", "pip install -e .[ui]"),
    ("Jinja2", "jinja2", "pip install -e .[report]"),
    ("httpx", "httpx", "pip install -e .[llm]"),
)


SYSTEM_DEPENDENCIES: tuple[tuple[str, str, str], ...] = (
    ("Node.js", "node", "brew install node"),
    ("npm", "npm", "brew install node"),
    ("Git", "git", "brew install git"),
)


def _command_version(binary: str) -> str | None:
    try:
        proc = subprocess.run([binary, "--version"], capture_output=True, text=True, check=False, timeout=2.0)
    except FileNotFoundError:
        return None
    except Exception:
        return None
    output = proc.stdout.strip() or proc.stderr.strip()
    return output or None


def check_python_version() -> HealthCheck:
    ver = sys.version_info
    name = "Python"
    if ver.major == 3 and ver.minor in (11, 12):
        message = f"{ver.major}.{ver.minor}.{ver.micro}"
        return HealthCheck(name=name, status=HealthStatus.OK, message=message)
    if ver.major == 3 and ver.minor == 13:
        return HealthCheck(
            name=name,
            status=HealthStatus.WARNING,
            message=f"{ver.major}.{ver.minor}.{ver.micro}",
            suggestion="Some dependencies may not yet support Python 3.13; prefer 3.11 or 3.12.",
        )
    return HealthCheck(
        name=name,
        status=HealthStatus.ERROR,
        message=f"{ver.major}.{ver.minor}.{ver.micro}",
        suggestion="Install Python 3.11 or 3.12 (e.g., `brew install python@3.12`).",
    )


def check_installed_extras() -> List[HealthCheck]:
    results: List[HealthCheck] = []
    for label, module, hint in OPTIONAL_FEATURES:
        spec = importlib.util.find_spec(module)
        if spec is None:
            results.append(
                HealthCheck(
                    name=f"{label} module",
                    status=HealthStatus.WARNING,
                    message="Not installed",
                    suggestion=hint,
                )
            )
        else:
            results.append(
                HealthCheck(
                    name=f"{label} module",
                    status=HealthStatus.OK,
                    message="Installed",
                )
            )
    return results


def check_system_dependencies() -> List[HealthCheck]:
    checks: List[HealthCheck] = []
    for label, binary, hint in SYSTEM_DEPENDENCIES:
        path = shutil.which(binary)
        if path is None:
            checks.append(
                HealthCheck(
                    name=label,
                    status=HealthStatus.WARNING,
                    message="Not found on PATH",
                    suggestion=hint,
                )
            )
        else:
            version = _command_version(binary)
            message = version or f"Found at {path}"
            checks.append(
                HealthCheck(
                    name=label,
                    status=HealthStatus.OK,
                    message=message,
                )
            )

    browsers_path = _detect_playwright_browser_path()
    if browsers_path and browsers_path.exists() and any(browsers_path.iterdir()):
        checks.append(
            HealthCheck(
                name="Playwright browsers",
                status=HealthStatus.OK,
                message=f"Installed at {browsers_path}",
            )
        )
    else:
        checks.append(
            HealthCheck(
                name="Playwright browsers",
                status=HealthStatus.WARNING,
                message="No browsers installed",
                suggestion="Install with `npx playwright install --with-deps`.",
            )
        )
    return checks


def _detect_playwright_browser_path() -> Path:
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom:
        return Path(custom).expanduser()
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return (base / "ms-playwright").resolve()
    return (Path.home() / ".cache" / "ms-playwright").resolve()


def llm_extras_installed() -> bool:
    return importlib.util.find_spec("httpx") is not None


def check_ollama() -> HealthCheck:
    if shutil.which("ollama") is None:
        return HealthCheck(
            name="Ollama",
            status=HealthStatus.WARNING,
            message="Ollama CLI not found",
            suggestion="Install with `brew install ollama` and run `ollama serve`.",
        )
    try:
        import httpx  # type: ignore

        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if response.status_code == 200:
            models = response.json().get("models", []) or []
            if models:
                names = ", ".join(model.get("name", "") for model in models[:3])
                if len(models) > 3:
                    names += ", ..."
                message = f"Running (models: {names})"
            else:
                message = "Running (no models downloaded)"
            return HealthCheck(name="Ollama", status=HealthStatus.OK, message=message)
        return HealthCheck(
            name="Ollama",
            status=HealthStatus.WARNING,
            message=f"Unexpected response: HTTP {response.status_code}",
            suggestion="Ensure `ollama serve` is running locally.",
        )
    except Exception:
        return HealthCheck(
            name="Ollama",
            status=HealthStatus.WARNING,
            message="Unable to connect to Ollama on localhost:11434",
            suggestion="Run `ollama serve` before using LLM features.",
        )


async def _probe_mcp_server() -> tuple[HealthStatus, str, str | None]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "qaagent-mcp",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return (
            HealthStatus.ERROR,
            "qaagent-mcp entrypoint not found.",
            "Install MCP extras: pip install -e .[mcp]",
        )
    await asyncio.sleep(0.2)
    if proc.returncode is not None:
        stderr = ""
        if proc.stderr:
            try:
                stderr = (await proc.stderr.read()).decode().strip()
            except Exception:
                stderr = ""
        return (
            HealthStatus.ERROR,
            "MCP server exited during startup" + (f": {stderr.splitlines()[-1]}" if stderr else ""),
            "Reinstall MCP extras: pip install -e .[mcp]",
        )
    assert proc.stdin and proc.stdout
    init_msg = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "1.0"},
        }
    ) + "\n"
    try:
        proc.stdin.write(init_msg.encode())
        await proc.stdin.drain()
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=3.0)
        payload = json.loads(line.decode())
        status = HealthStatus.OK if "result" in payload else HealthStatus.WARNING
        message = "Handshake succeeded" if status is HealthStatus.OK else "Received unexpected payload"
        suggestion = None if status is HealthStatus.OK else "Inspect qaagent-mcp output for details."
    except asyncio.TimeoutError:
        message = "Timed out waiting for MCP handshake."
        stderr = ""
        if proc.stderr:
            try:
                stderr = (await proc.stderr.read()).decode().strip()
            except Exception:
                stderr = ""
        suggestion = "Ensure no other process is blocking qaagent-mcp and try again."
        if stderr:
            message += f" stderr: {stderr.splitlines()[-1]}"
        status = HealthStatus.WARNING
    except Exception as exc:  # noqa: BLE001
        message = f"MCP handshake failed: {exc}"
        suggestion = "Reinstall MCP extras: pip install -e .[mcp]"
        status = HealthStatus.ERROR
    finally:
        if proc.stdin:
            try:
                proc.stdin.close()
            except Exception:
                pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                proc.kill()
    return status, message, suggestion


def check_mcp_server() -> HealthCheck:
    status, message, suggestion = asyncio.run(_probe_mcp_server())
    return HealthCheck(name="MCP server", status=status, message=message, suggestion=suggestion)


def run_health_checks() -> List[HealthCheck]:
    checks: List[HealthCheck] = [check_python_version()]
    checks.extend(check_installed_extras())
    checks.extend(check_system_dependencies())
    if llm_extras_installed():
        checks.append(check_ollama())
    else:
        checks.append(
            HealthCheck(
                name="Ollama",
                status=HealthStatus.WARNING,
                message="LLM extras not installed",
                suggestion="Install with `pip install -e .[llm]` to enable LLM features.",
            )
        )
    checks.append(check_mcp_server())
    return checks


def checks_to_json(checks: Iterable[HealthCheck]) -> list[dict[str, str | None]]:
    return [
        {
            "name": check.name,
            "status": check.status.value,
            "message": check.message,
            "suggestion": check.suggestion,
        }
        for check in checks
    ]
