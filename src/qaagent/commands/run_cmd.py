"""Test runner commands for the qaagent CLI."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

import typer
from rich import print

from ._helpers import console, module_available
from qaagent.tools import ensure_dir, run_command, which
from qaagent.config import load_config_compat, load_active_profile
from qaagent.openapi_utils import (
    find_openapi_candidates,
    load_openapi,
    enumerate_operations,
)
from qaagent.a11y import run_axe
from qaagent.sitemap import fetch_sitemap_urls


def pytest_run(
    path: str = typer.Option("tests", help="Path to tests directory or file"),
    junit: bool = typer.Option(True, help="Emit JUnit XML"),
    outdir: str = typer.Option("reports/pytest", help="Output directory for reports"),
    cov: bool = typer.Option(False, help="Enable pytest-cov and write coverage reports"),
    cov_target: str = typer.Option("src", help="Coverage target (package or path)"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Run pytest with optional JUnit output."""
    if which("pytest") is None:
        print("[red]pytest is not installed. Install base deps: pip install -e .[/red]")
        raise typer.Exit(code=2)

    out = Path(outdir)
    ensure_dir(out)
    cmd = ["pytest", path, "-q"]
    if junit:
        cmd += ["--junitxml", str(out / "junit.xml")]
    if cov:
        cov_xml = Path("reports/coverage/coverage.xml")
        cov_html_dir = Path("reports/coverage_html")
        ensure_dir(cov_xml.parent)
        ensure_dir(cov_html_dir)
        import importlib.util as _iu
        if _iu.find_spec("pytest_cov") is None:
            print("[yellow]pytest-cov is not installed. Install extras: pip install -e .[cov][/yellow]")
        else:
            cmd += [
                f"--cov={cov_target}",
                f"--cov-report=xml:{cov_xml}",
                f"--cov-report=html:{cov_html_dir}",
                "--cov-report=term",
            ]
    result = run_command(cmd)

    if json_out:
        print(json.dumps({"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}))
    else:
        print("[bold]Return code:[/bold]", result.returncode)
        if result.stdout:
            console.rule("pytest stdout (tail)")
            print(result.stdout)
        if result.stderr:
            console.rule("pytest stderr (tail)")
            print(result.stderr)
    raise typer.Exit(code=result.returncode)


def schemathesis_run(
    openapi: Optional[str] = typer.Option(None, help="Path or URL to OpenAPI/Swagger spec (falls back to config or detection)"),
    base_url: Optional[str] = typer.Option(None, help="Base URL of the API under test (falls back to config)"),
    outdir: str = typer.Option("reports/schemathesis", help="Output directory for reports"),
    auth_header: Optional[str] = typer.Option(None, help="Auth header name, e.g., Authorization"),
    auth_token_env: Optional[str] = typer.Option(None, help="Env var containing token (value will be prefixed)"),
    auth_prefix: str = typer.Option("Bearer ", help="String prefix for token value, e.g., 'Bearer '"),
    timeout: Optional[float] = typer.Option(None, help="Optional request timeout (seconds)"),
    tag: Optional[List[str]] = typer.Option(None, help="Filter by tag (repeatable)"),
    operation_id: Optional[List[str]] = typer.Option(None, help="Filter by operationId (repeatable)"),
    endpoint_pattern: Optional[str] = typer.Option(None, help="Regex to filter endpoint paths"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Run Schemathesis property-based tests against an OpenAPI target."""
    if which("schemathesis") is None:
        print("[red]schemathesis is not installed. Install API extras: pip install -e .[api][/red]")
        raise typer.Exit(code=2)

    cfg = load_config_compat()

    # Try workspace first if no openapi specified
    if not openapi:
        try:
            from qaagent.workspace import Workspace
            active_entry, _ = load_active_profile()
            ws = Workspace()
            workspace_spec = ws.get_openapi_path(active_entry.name, format="json")
            if workspace_spec.exists():
                openapi = str(workspace_spec)
                console.print(f"[cyan]Using OpenAPI spec from workspace: {workspace_spec}[/cyan]")
        except Exception:
            pass  # Fall through to config

    if not openapi and cfg and cfg.api.openapi:
        openapi = cfg.api.openapi
    if not base_url and cfg and cfg.api.base_url:
        base_url = cfg.api.base_url
    if not auth_header and cfg:
        auth_header = cfg.api.auth.header_name
    if not auth_token_env and cfg:
        auth_token_env = cfg.api.auth.token_env
    if auth_prefix == "Bearer " and cfg:
        auth_prefix = cfg.api.auth.prefix or auth_prefix
    if timeout is None and cfg:
        timeout = cfg.api.timeout
    if not tag and cfg and cfg.api.tags:
        tag = cfg.api.tags
    if not operation_id and cfg and cfg.api.operations:
        operation_id = cfg.api.operations
    if not endpoint_pattern and cfg and cfg.api.endpoint_pattern:
        endpoint_pattern = cfg.api.endpoint_pattern

    # Try to detect openapi if missing
    if not openapi:
        candidates = find_openapi_candidates(Path.cwd())
        if candidates:
            openapi = candidates[0].as_posix()

    if not openapi:
        print("[red]OpenAPI spec not provided or detected. Use --openapi or create .qaagent.toml[/red]")
        raise typer.Exit(code=2)
    if not base_url:
        print("[red]Base URL not provided. Use --base-url or set in .qaagent.toml[/red]")
        raise typer.Exit(code=2)

    out = Path(outdir)
    ensure_dir(out)
    cmd = [
        "schemathesis",
        "run",
        openapi,
        "--url",
        base_url,
        "--checks=all",
        "--report", "junit",
        "--report-junit-path",
        str(out / "junit.xml"),
    ]

    # Include auth header if available
    token_val = None
    if auth_token_env:
        token_val = os.environ.get(auth_token_env)
    if token_val:
        header_value = f"{auth_prefix}{token_val}" if auth_prefix else token_val
        cmd += ["--header", f"{auth_header or 'Authorization'}: {header_value}"]

    # Filters
    if tag:
        for t in tag:
            cmd += ["--include-tag", t]
    if operation_id:
        for op in operation_id:
            cmd += ["--include-operation-id", op]
    if endpoint_pattern:
        cmd += ["--include-path-regex", endpoint_pattern]
    if timeout is not None:
        cmd += ["--request-timeout", str(timeout)]

    result = run_command(cmd)
    if json_out:
        print(json.dumps({"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}))
    else:
        print("[bold]Return code:[/bold]", result.returncode)
        if result.stdout:
            console.rule("schemathesis stdout (tail)")
            print(result.stdout)
        if result.stderr:
            console.rule("schemathesis stderr (tail)")
            print(result.stderr)

    # Coverage summary (best effort)
    try:
        from qaagent.report import parse_junit
        from qaagent.openapi_utils import covered_operations_from_junit_case_names

        junit_path = out / "junit.xml"
        suites = parse_junit(junit_path)
        case_names = [c.name for s in suites for c in s.cases]

        covered = set(covered_operations_from_junit_case_names(case_names))
        spec = load_openapi(openapi)
        ops = enumerate_operations(spec)
        total_ops = len(ops)
        covered_count = sum(1 for op in ops if (op.method, op.path) in covered)
        if total_ops:
            pct = covered_count * 100.0 / total_ops
            print(f"[bold]Operation coverage:[/bold] {covered_count}/{total_ops} ({pct:.1f}%)")
    except Exception:
        pass
    raise typer.Exit(code=result.returncode)


def playwright_install():
    """Install Playwright browsers for Python."""
    if not module_available("playwright"):
        print("[red]Playwright for Python is not installed. Install UI extras: pip install -e .[ui][/red]")
        raise typer.Exit(code=2)
    py = os.sys.executable
    cmd = [py, "-m", "playwright", "install"]
    result = run_command(cmd)
    print("[bold]Return code:[/bold]", result.returncode)
    if result.stdout:
        console.rule("playwright install stdout (tail)")
        print(result.stdout)
    if result.stderr:
        console.rule("playwright install stderr (tail)")
        print(result.stderr)
    raise typer.Exit(code=result.returncode)


def playwright_scaffold(dest: str = typer.Option("tests/ui", help="Directory for UI tests")):
    """Create a basic Playwright pytest smoke test."""
    if not module_available("pytest"):
        print("[red]pytest not found. Install base deps: pip install -e .[/red]")
        raise typer.Exit(code=2)
    if not module_available("pytest_playwright"):
        print("[yellow]pytest-playwright not found. UI tests work best with: pip install -e .[ui][/yellow]")

    dest_path = Path(dest)
    ensure_dir(dest_path)
    test_file = dest_path / "test_smoke.py"
    if test_file.exists():
        print(f"[yellow]File already exists: {test_file}[/yellow]")
    else:
        content = """
import os
import pytest


def test_homepage_title(page):
    base_url = os.environ.get("BASE_URL", "https://example.com")
    page.goto(base_url)
    title = page.title()
    assert "Example" in title


def test_homepage_h1(page):
    base_url = os.environ.get("BASE_URL", "https://example.com")
    page.goto(base_url)
    h1 = page.locator("h1")
    assert h1.first().inner_text().strip() != ""
""".lstrip()
        test_file.write_text(content)
        print(f"[green]Created[/green] {test_file}")


def ui_run(
    path: str = typer.Option("tests/ui", help="Tests path to run"),
    base_url: Optional[str] = typer.Option(None, help="Base URL for UI tests (exported as BASE_URL)"),
    headed: bool = typer.Option(False, help="Run headed (visible browser)"),
    browser: str = typer.Option("chromium", help="Browser: chromium|firefox|webkit"),
    junit: bool = typer.Option(True, help="Emit JUnit XML"),
    outdir: str = typer.Option("reports/ui", help="Output directory for reports"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Run Playwright UI tests via pytest-playwright with reports."""
    if not module_available("pytest"):
        print("[red]pytest not found. Install base deps: pip install -e .[/red]")
        raise typer.Exit(code=2)
    if not module_available("pytest_playwright"):
        print("[red]pytest-playwright not found. Install UI extras: pip install -e .[ui][/red]")
        raise typer.Exit(code=2)

    out = Path(outdir)
    ensure_dir(out)

    cmd = [
        "pytest",
        path,
        "-q",
        f"--browser={browser}",
        "--tracing=retain-on-failure",
        "--video=retain-on-failure",
        "--screenshot=only-on-failure",
    ]
    if headed:
        cmd.append("--headed")
    if junit:
        cmd += ["--junitxml", str(out / "junit.xml")]
    if module_available("pytest_html"):
        cmd += ["--html", str(out / "report.html"), "--self-contained-html"]

    env = {}
    if base_url:
        env["BASE_URL"] = base_url

    result = run_command(cmd, env=env)
    if json_out:
        print(json.dumps({"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}))
    else:
        print("[bold]Return code:[/bold]", result.returncode)
        if result.stdout:
            console.rule("pytest (ui) stdout (tail)")
            print(result.stdout)
        if result.stderr:
            console.rule("pytest (ui) stderr (tail)")
            print(result.stderr)
    raise typer.Exit(code=result.returncode)


def perf_scaffold(dest: str = typer.Option("perf", help="Directory for Locust files")):
    """Create a minimal locustfile.py that uses BASE_URL as host."""
    d = Path(dest)
    ensure_dir(d)
    locustfile = d / "locustfile.py"
    if locustfile.exists():
        print(f"[yellow]File exists:[/yellow] {locustfile}")
        return
    content = """
from locust import HttpUser, task, between
import os


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    host = os.environ.get("BASE_URL", "http://localhost:8000")

    @task
    def index(self):
        self.client.get("/")
""".lstrip()
    locustfile.write_text(content)
    print(f"[green]Created[/green] {locustfile}")


def perf_run(
    locustfile: str = typer.Option("perf/locustfile.py", help="Path to locustfile.py"),
    users: int = typer.Option(10, help="Number of users"),
    spawn_rate: float = typer.Option(2.0, help="Users spawned per second"),
    run_time: str = typer.Option("1m", help="Run time, e.g., 1m, 30s"),
    outdir: str = typer.Option("reports/perf", help="Output directory"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Run Locust in headless mode and write CSV stats."""
    if which("locust") is None:
        print("[red]Locust not installed. Install perf extras: pip install -e .[perf][/red]")
        raise typer.Exit(code=2)
    ensure_dir(Path(outdir))
    csv_base = Path(outdir) / "locust"
    cmd = [
        "locust",
        "-f",
        locustfile,
        "--headless",
        "-u",
        str(users),
        "-r",
        str(spawn_rate),
        "--run-time",
        run_time,
        "--csv",
        str(csv_base),
        "--only-summary",
    ]
    result = run_command(cmd)
    if json_out:
        print(json.dumps({"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "csv_base": str(csv_base)}))
    else:
        print("[bold]Return code:[/bold]", result.returncode)
        if result.stdout:
            console.rule("locust stdout (tail)")
            print(result.stdout)
        if result.stderr:
            console.rule("locust stderr (tail)")
            print(result.stderr)
    raise typer.Exit(code=result.returncode)


def lighthouse_audit(
    url: Optional[str] = typer.Option(None, help="URL to audit (defaults to BASE_URL)"),
    outdir: str = typer.Option("reports/lighthouse", help="Output directory"),
    categories: str = typer.Option("performance,accessibility,best-practices,seo", help="Comma-separated categories"),
    device: str = typer.Option("desktop", help="emulation: desktop|mobile"),
    disable_storage_reset: bool = typer.Option(False, help="Keep storage state"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Run Lighthouse via npx or installed lighthouse and save HTML+JSON reports."""
    target = url or os.environ.get("BASE_URL")
    if not target:
        print("[red]Provide --url or set BASE_URL[/red]")
        raise typer.Exit(code=2)
    ensure_dir(Path(outdir))
    html = Path(outdir) / "report.html"
    json_path = Path(outdir) / "report.json"

    # Prefer installed lighthouse, fallback to npx
    if which("lighthouse"):
        base_cmd = ["lighthouse"]
    elif which("npx"):
        base_cmd = ["npx", "-y", "lighthouse"]
    else:
        print("[red]lighthouse or npx not found. Install Node LTS and Lighthouse.[/red]")
        raise typer.Exit(code=2)

    cmd = base_cmd + [
        target,
        "--quiet",
        f"--only-categories={categories}",
        f"--preset={'desktop' if device=='desktop' else 'mobile'}",
        "--output=json",
        "--output=html",
        f"--output-path={html}",
        f"--save-assets",
    ]
    if disable_storage_reset:
        cmd.append("--disable-storage-reset")

    result = run_command(cmd)
    if json_path.exists():
        pass
    else:
        for p in Path(outdir).glob("*.report.json"):
            p.rename(json_path)
            break

    if json_out:
        print(json.dumps({
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "html": html.as_posix(),
            "json": json_path.as_posix() if json_path.exists() else None,
        }))
    else:
        print("[bold]Return code:[/bold]", result.returncode)
        if result.stdout:
            console.rule("lighthouse stdout (tail)")
            print(result.stdout)
        if result.stderr:
            console.rule("lighthouse stderr (tail)")
            print(result.stderr)
    raise typer.Exit(code=result.returncode)


def a11y_run(
    url: Optional[List[str]] = typer.Option(None, help="URL(s) to check. Repeatable."),
    outdir: str = typer.Option("reports/a11y", help="Output directory"),
    tag: Optional[List[str]] = typer.Option(None, help="axe tags to runOnly (e.g., wcag2a, wcag2aa)"),
    browser: str = typer.Option("chromium", help="Browser: chromium|firefox|webkit"),
    axe_url: str = typer.Option("https://cdn.jsdelivr.net/npm/axe-core@4.7.0/axe.min.js", help="axe-core script URL"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Run accessibility checks with axe-core via Playwright and save a Markdown + JSON report."""
    if not url:
        env_url = os.environ.get("BASE_URL")
        if env_url:
            url = [env_url]
    if not url:
        print("[red]Provide at least one --url or set BASE_URL[/red]")
        raise typer.Exit(code=2)

    meta = run_axe(urls=url, outdir=Path(outdir), tags=tag, axe_source_url=axe_url, browser=browser)
    if json_out:
        print(json.dumps(meta))
    else:
        print(f"[green]A11y report:[/green] {meta['output_markdown']} | violations groups: {meta['violations']}")


def a11y_from_sitemap(
    base_url: str = typer.Option(..., help="Site base URL where sitemap.xml lives"),
    limit: int = typer.Option(30, help="Max URLs to audit"),
    outdir: str = typer.Option("reports/a11y", help="Output directory"),
    tag: Optional[List[str]] = typer.Option(None, help="axe tags to runOnly (e.g., wcag2a, wcag2aa)"),
    browser: str = typer.Option("chromium", help="Browser: chromium|firefox|webkit"),
    axe_url: str = typer.Option("https://cdn.jsdelivr.net/npm/axe-core@4.7.0/axe.min.js", help="axe-core script URL"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Fetch sitemap.xml and run a11y checks on up to N URLs."""
    try:
        urls = fetch_sitemap_urls(base_url, limit=limit)
    except Exception as e:  # noqa: BLE001
        print(f"[red]{e}[/red]")
        raise typer.Exit(code=2)
    if not urls:
        print("[yellow]No URLs found in sitemap[/yellow]")
        raise typer.Exit(code=2)
    meta = run_axe(urls=urls, outdir=Path(outdir), tags=tag, axe_source_url=axe_url, browser=browser)
    if json_out:
        print(json.dumps(meta))
    else:
        print(f"[green]A11y report:[/green] {meta['output_markdown']} | violations groups: {meta['violations']}")


def run_all(
    out: Optional[str] = typer.Option(None, help="Output directory for results"),
):
    """Run all enabled test suites via the orchestrator."""
    from qaagent.config import load_active_profile
    from qaagent.runners.orchestrator import RunOrchestrator

    try:
        _, profile = load_active_profile()
    except Exception:
        console.print("[red]No active profile. Use `qaagent use <target>` first.[/red]")
        raise typer.Exit(code=2)

    output_dir = Path(out) if out else Path("reports")
    orchestrator = RunOrchestrator(config=profile, output_dir=output_dir)

    console.print("[cyan]Running all enabled test suites...[/cyan]")
    result = orchestrator.run_all()

    # Print summary
    console.print()
    console.print(f"[bold]Results:[/bold]")
    for suite_name, suite_result in result.suites.items():
        status = "[green]PASS[/green]" if suite_result.success else "[red]FAIL[/red]"
        console.print(
            f"  {suite_name}: {status} "
            f"({suite_result.passed} passed, {suite_result.failed} failed, "
            f"{suite_result.errors} errors, {suite_result.skipped} skipped) "
            f"[{suite_result.duration:.1f}s]"
        )

    console.print()
    total_status = "[green]ALL PASSED[/green]" if result.success else "[red]FAILURES[/red]"
    console.print(
        f"Total: {total_status} - "
        f"{result.total_passed} passed, {result.total_failed} failed, "
        f"{result.total_errors} errors [{result.total_duration:.1f}s]"
    )

    if result.diagnostic_summary and result.diagnostic_summary.summary_text:
        console.print()
        console.print("[yellow]Failure Analysis:[/yellow]")
        console.print(f"  {result.diagnostic_summary.summary_text}")

    if result.run_handle:
        console.print(f"Evidence: {result.run_handle.run_dir}")

    if not result.success:
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    """Register all test runner commands on the main app."""
    app.command("pytest-run")(pytest_run)
    app.command("schemathesis-run")(schemathesis_run)
    app.command("playwright-install")(playwright_install)
    app.command("playwright-scaffold")(playwright_scaffold)
    app.command("ui-run")(ui_run)
    app.command("perf-scaffold")(perf_scaffold)
    app.command("perf-run")(perf_run)
    app.command("lighthouse-audit")(lighthouse_audit)
    app.command("a11y-run")(a11y_run)
    app.command("a11y-from-sitemap")(a11y_from_sitemap)
    app.command("run-all")(run_all)
