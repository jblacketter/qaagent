"""Flow recording command for qaagent CLI."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import typer
from rich.table import Table

from ._helpers import console
from qaagent.config import load_active_profile
from qaagent.recording import (
    export_behave_assets,
    export_playwright_spec,
    record_flow,
    save_recording,
)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")


def _safe_name(value: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", value.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "recorded_flow"


def _pick_profile_environment(profile):
    if not profile or not getattr(profile, "app", None):
        return None

    app = profile.app
    for env_name in ("dev", "staging", "production"):
        env = app.get(env_name)
        if env and env.base_url:
            return env
    for env_name in ("dev", "staging", "production"):
        env = app.get(env_name)
        if env:
            return env
    for env in app.values():
        return env
    return None


def _parse_extra_headers(values: Optional[List[str]]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for raw in values or []:
        item = raw.strip()
        if not item:
            continue
        if ":" in item:
            key, value = item.split(":", 1)
        elif "=" in item:
            key, value = item.split("=", 1)
        else:
            raise ValueError(f"Invalid --header value '{raw}'. Use KEY:VALUE or KEY=VALUE.")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid --header value '{raw}'. Header name cannot be empty.")
        headers[key] = value
    return headers


def record(
    name: str = typer.Option("recorded_flow", "--name", help="Flow name used for recording and exports"),
    url: Optional[str] = typer.Option(None, "--url", help="Start URL (falls back to active profile base_url)"),
    browser: str = typer.Option("chromium", "--browser", help="Browser engine: chromium|firefox|webkit"),
    headed: bool = typer.Option(False, "--headed", help="Run headed browser (default is headless)"),
    timeout: float = typer.Option(30.0, "--timeout", min=1.0, help="Recording timeout in seconds"),
    max_actions: int = typer.Option(100, "--max-actions", min=1, help="Max actions to capture"),
    out_dir: str = typer.Option(".qaagent/recordings", "--out-dir", help="Directory for recording artifacts"),
    storage_state: Optional[str] = typer.Option(
        None,
        "--storage-state",
        help="Optional Playwright storage state JSON path",
    ),
    header: Optional[List[str]] = typer.Option(
        None,
        "--header",
        help="Extra request header KEY:VALUE (repeatable)",
    ),
    auth_header: Optional[str] = typer.Option(
        None,
        "--auth-header",
        help="Auth header name (defaults from profile auth settings)",
    ),
    auth_token_env: Optional[str] = typer.Option(
        None,
        "--auth-token-env",
        help="Env var containing auth token value",
    ),
    auth_prefix: str = typer.Option("Bearer ", "--auth-prefix", help="Prefix for auth token header value"),
    export: str = typer.Option("both", "--export", help="Export target: playwright|behave|both|none"),
):
    """Record browser interactions and export tests."""
    export_mode = (export or "both").strip().lower()
    if export_mode not in {"playwright", "behave", "both", "none"}:
        typer.echo("Invalid --export value. Use one of: playwright, behave, both, none.")
        raise typer.Exit(code=2)

    active_entry = None
    active_profile = None
    project_root = Path.cwd()
    try:
        active_entry, active_profile = load_active_profile()
    except Exception:
        active_entry = None
        active_profile = None
    else:
        project_root = active_entry.resolved_path()

    env = _pick_profile_environment(active_profile) if active_profile else None
    if env and not url and env.base_url:
        url = env.base_url

    if not url:
        typer.echo("Provide --url or configure app.dev.base_url in the active profile.")
        raise typer.Exit(code=2)

    try:
        headers = _parse_extra_headers(header)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2)

    if env and env.headers:
        merged = dict(env.headers)
        merged.update(headers)
        headers = merged

    if env and env.auth:
        auth_header = auth_header or env.auth.header_name
        auth_token_env = auth_token_env or env.auth.token_env
        if auth_prefix == "Bearer " and env.auth.prefix:
            auth_prefix = env.auth.prefix

    if auth_token_env:
        token = os.environ.get(auth_token_env)
        if token:
            header_name = auth_header or "Authorization"
            headers[header_name] = f"{auth_prefix}{token}" if auth_prefix else token
        elif auth_header:
            console.print(
                f"[yellow]Auth token env '{auth_token_env}' is unset; continuing without {auth_header} header.[/yellow]"
            )

    storage_state_path: Optional[Path] = None
    if storage_state:
        storage_state_path = Path(storage_state)
    elif env and active_profile and active_profile.tests.e2e and active_profile.tests.e2e.auth_setup:
        candidate = project_root / ".auth" / "state.json"
        if candidate.exists():
            storage_state_path = candidate

    flow = record_flow(
        name=name,
        start_url=url,
        timeout_seconds=timeout,
        max_actions=max_actions,
        browser=browser,
        headless=not headed,
        headers=headers or None,
        storage_state_path=storage_state_path,
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(out_dir) / f"{timestamp}_{_safe_name(name)}"
    recording_file = save_recording(flow, run_dir)

    playwright_path: Optional[Path] = None
    feature_path: Optional[Path] = None
    steps_path: Optional[Path] = None
    safe = _safe_name(name)

    if export_mode in {"playwright", "both"}:
        playwright_path = export_playwright_spec(flow, Path("tests/qaagent/e2e") / f"recorded_{safe}.spec.ts")
    if export_mode in {"behave", "both"}:
        feature_path, steps_path = export_behave_assets(
            flow,
            Path("tests/qaagent/behave/features") / f"recorded_{safe}.feature",
            Path("tests/qaagent/behave/steps") / "recorded_steps.py",
        )

    table = Table(title="Recording Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Flow", flow.name)
    table.add_row("Start URL", flow.start_url)
    table.add_row("Captured actions", str(len(flow.actions)))
    table.add_row("Recording JSON", str(recording_file))
    if playwright_path:
        table.add_row("Playwright export", str(playwright_path))
    if feature_path:
        table.add_row("Behave feature", str(feature_path))
    if steps_path:
        table.add_row("Behave steps", str(steps_path))
    console.print(table)


def register(app: typer.Typer) -> None:
    """Register recording command on main app."""
    app.command("record")(record)

