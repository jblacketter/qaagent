from __future__ import annotations

import json
import os
from pathlib import Path
import importlib.util
from typing import Optional, List

import typer
from pydantic import BaseModel
from rich import print
from rich.console import Console
from rich.table import Table

from .tools import ensure_dir, run_command, which
from . import __version__
from .report import generate_report
from .config import load_config, write_default_config, write_env_example
from .openapi_utils import (
    find_openapi_candidates,
    load_openapi,
    enumerate_operations,
    is_url,
    probe_spec_from_base_url,
)
from .a11y import run_axe
from .llm import generate_api_tests_from_spec, summarize_findings_text, llm_available
from .sitemap import fetch_sitemap_urls
import webbrowser
import zipfile


app = typer.Typer(help="QA Agent CLI: analyze, test, and expose tools via MCP")
console = Console()


class AnalyzeSummary(BaseModel):
    root: str
    language_hints: list[str]
    frameworks: list[str]
    detected: list[str]
    recommendations: list[str]


def _detect_stack(root: Path) -> AnalyzeSummary:
    language_hints: list[str] = []
    frameworks: list[str] = []
    detected: list[str] = []

    files = {p.name.lower(): p for p in root.glob("**/*") if p.is_file() and len(p.parts) < 8}

    if "pyproject.toml" in files or "requirements.txt" in files:
        language_hints.append("python")
        detected.append("pyproject/requirements")
    if "package.json" in files:
        language_hints.append("javascript")
        detected.append("package.json")
    if any(n in files for n in ("openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.json")):
        frameworks.append("openapi")
        detected.append("openapi/swagger spec")
    if "dockerfile" in files:
        detected.append("dockerfile")
    if any(n in files for n in ("pytest.ini", "conftest.py")):
        frameworks.append("pytest")
    if any("playwright" in n for n in files):
        frameworks.append("playwright")

    recs: list[str] = []
    if "openapi" in frameworks:
        recs.append("Use Schemathesis for property-based API tests")
    if "pytest" not in frameworks and "python" in language_hints:
        recs.append("Initialize pytest and add smoke tests")
    if "playwright" not in frameworks:
        recs.append("Add Playwright UI smoke flows with HTML report & video")
    recs.append("Aggregate results into a QA Findings report (Markdown/HTML)")

    return AnalyzeSummary(
        root=str(root),
        language_hints=sorted(set(language_hints)),
        frameworks=sorted(set(frameworks)),
        detected=sorted(set(detected)),
        recommendations=recs,
    )


@app.command()
def analyze(path: str = typer.Argument(".", help="Project root to analyze")):
    """Heuristic repo analysis to propose a QA plan."""
    root = Path(path).resolve()
    if not root.exists():
        typer.echo(f"Path not found: {root}")
        raise typer.Exit(code=2)

    summary = _detect_stack(root)

    table = Table(title=f"QA Analysis: {summary.root}")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Values", style="white")
    table.add_row("Language Hints", ", ".join(summary.language_hints) or "-")
    table.add_row("Frameworks", ", ".join(summary.frameworks) or "-")
    table.add_row("Detected", ", ".join(summary.detected) or "-")
    console.print(table)

    console.rule("Recommendations")
    for i, r in enumerate(summary.recommendations, start=1):
        print(f"[green]{i}.[/green] {r}")


@app.command("pytest-run")
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
        # check plugin
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


@app.command("schemathesis-run")
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

    cfg = load_config()
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
        "--base-url",
        base_url,
        "--checks=all",
        "--hypothesis-deadline=500",
        "--junit-xml",
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
            cmd += ["--tag", t]
    if operation_id:
        for op in operation_id:
            cmd += ["--operation-id", op]
    if endpoint_pattern:
        cmd += ["--endpoint", endpoint_pattern]
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
        from .report import parse_junit
        from .openapi_utils import enumerate_operations

        junit_path = out / "junit.xml"
        suites = parse_junit(junit_path)
        case_names = [c.name for s in suites for c in s.cases]
        from .openapi_utils import covered_operations_from_junit_case_names

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


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


@app.command("playwright-install")
def playwright_install():
    """Install Playwright browsers for Python."""
    if not _module_available("playwright"):
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


@app.command("playwright-scaffold")
def playwright_scaffold(dest: str = typer.Option("tests/ui", help="Directory for UI tests")):
    """Create a basic Playwright pytest smoke test."""
    if not _module_available("pytest"):
        print("[red]pytest not found. Install base deps: pip install -e .[/red]")
        raise typer.Exit(code=2)
    if not _module_available("pytest_playwright"):
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


@app.command("ui-run")
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
    if not _module_available("pytest"):
        print("[red]pytest not found. Install base deps: pip install -e .[/red]")
        raise typer.Exit(code=2)
    if not _module_available("pytest_playwright"):
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
    if _module_available("pytest_html"):
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


@app.command("perf-scaffold")
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


@app.command("perf-run")
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


@app.command("lighthouse-audit")
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
    # Lighthouse writes JSON next to HTML when output-path is set; ensure copy/move
    # Try to find the JSON file from stdout hint or default path
    if json_path.exists():
        pass
    else:
        # Attempt to detect a .report.json near the HTML path
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


@app.command("report")
def report(
    out: str = typer.Option("reports/findings.md", help="Output file path (.md or .html)"),
    sources: Optional[List[str]] = typer.Option(None, help="Optional JUnit XML files to include; defaults searched"),
    title: str = typer.Option("QA Findings", help="Report title"),
    fmt: str = typer.Option("markdown", help="Report format: markdown|html"),
    json_out: bool = typer.Option(False, help="Print JSON result metadata"),
):
    """Generate a consolidated QA Findings report (Markdown)."""
    # Convenience: if html requested but extension is .md, flip it
    if fmt.lower() == "html" and out.lower().endswith(".md"):
        out = out[:-3] + ".html"
    result = generate_report(output=out, sources=sources, title=title, fmt=fmt)
    if json_out:
        print(json.dumps(result))
    else:
        print(f"[green]Report written:[/green] {result['output']}")
        print("Summary:")
        print(result["summary"]) 


@app.command("a11y-run")
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


@app.command("a11y-from-sitemap")
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


@app.command("mcp-stdio")
def mcp_stdio():
    """Run the MCP server over stdio."""
    try:
        # Lazy import to keep base install light
        from .mcp_server import run_stdio
    except Exception as e:  # noqa: BLE001
        print("[red]MCP server is unavailable. Ensure 'mcp' extra is installed.[/red]")
        print(str(e))
        raise typer.Exit(code=2)

    run_stdio()


@app.command()
def version():
    """Show version info."""
    data = {"qaagent": __version__, "python": os.sys.version.split()[0]}
    print(json.dumps(data))


@app.command()
def init():
    """Create a starter .qaagent.toml and .env.example if missing."""
    cfg_path = write_default_config()
    env_example = write_env_example()
    print(f"[green]Wrote[/green] {cfg_path}")
    print(f"[green]Wrote[/green] {env_example}")


@app.command("api-detect")
def api_detect(
    path: str = typer.Option(".", help="Root to search for OpenAPI files"),
    base_url: Optional[str] = typer.Option(None, help="If provided, probe common spec endpoints"),
    probe: bool = typer.Option(False, help="Probe base URL for spec endpoints"),
):
    """Find OpenAPI files and optionally probe a base URL for a spec endpoint."""
    root = Path(path)
    files = find_openapi_candidates(root)
    table = Table(title="OpenAPI Detection")
    table.add_column("Source", style="cyan")
    table.add_column("Value")
    if files:
        for f in files:
            table.add_row("file", f.as_posix())
    else:
        table.add_row("file", "(none found)")

    found_url = None
    if base_url and probe:
        found_url = probe_spec_from_base_url(base_url)
        table.add_row("probe", found_url or "(not found)")

    console.print(table)

    # Print operation count if a spec is loadable
    target = (found_url or (files[0].as_posix() if files else None))
    if target:
        try:
            spec = load_openapi(target)
            ops = enumerate_operations(spec)
            print(f"[bold]Operations detected:[/bold] {len(ops)} from {target}")
        except Exception as e:  # noqa: BLE001
            print(f"[yellow]Could not parse spec from {target}: {e}[/yellow]")


@app.command("gen-tests")
def gen_tests(
    kind: str = typer.Option("api", help="Type of tests to generate: api|ui (api supported)"),
    openapi: Optional[str] = typer.Option(None, help="Path/URL to OpenAPI; auto-detect if omitted"),
    base_url: Optional[str] = typer.Option(None, help="Base URL for generated tests"),
    outdir: str = typer.Option("tests/api", help="Directory to write tests"),
    max_tests: int = typer.Option(12, help="Max tests to generate"),
    dry_run: bool = typer.Option(False, help="Print output instead of writing files"),
):
    """Generate test stubs. For now, supports API-only from OpenAPI. Falls back if no LLM."""
    if kind != "api":
        print("[red]Only kind=api is supported currently[/red]")
        raise typer.Exit(code=2)
    cfg = load_config()
    if not openapi and cfg and cfg.api.openapi:
        openapi = cfg.api.openapi
    if not base_url and cfg and cfg.api.base_url:
        base_url = cfg.api.base_url
    if not openapi:
        cands = find_openapi_candidates(Path.cwd())
        if cands:
            openapi = cands[0].as_posix()
    if not openapi:
        print("[red]OpenAPI not provided or detected[/red]")
        raise typer.Exit(code=2)
    if not base_url:
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")

    spec = load_openapi(openapi)
    code = generate_api_tests_from_spec(spec, base_url=base_url, max_tests=max_tests)
    if dry_run:
        console.rule("Generated tests (preview)")
        print(code)
        return
    dest = Path(outdir)
    ensure_dir(dest)
    path = dest / "test_generated_api.py"
    path.write_text(code, encoding="utf-8")
    print(f"[green]Wrote[/green] {path} (LLM={'yes' if llm_available() else 'no'})")


@app.command("summarize")
def summarize(
    findings: str = typer.Option("reports/findings.md", help="Findings file to base the summary on (regenerated if exists)"),
    fmt: str = typer.Option("markdown", help="Report format for re-generation (md or html)"),
    out: str = typer.Option("reports/summary.md", help="Executive summary output"),
):
    """Produce an executive summary using artifacts and (optionally) the local LLM."""
    # Re-generate a fresh report to get current metadata
    meta = generate_report(output=findings, fmt=fmt)
    summary = summarize_findings_text(meta)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(summary, encoding="utf-8")
    print(f"[green]Summary written:[/green] {out} (LLM={'yes' if llm_available() else 'no'})")


@app.command("open-report")
def open_report(path: str = typer.Option("reports/findings.html", help="Path to report HTML")):
    """Open the HTML report in the default browser."""
    p = Path(path)
    if not p.exists():
        print(f"[red]Report not found:[/red] {p}")
        raise typer.Exit(code=2)
    webbrowser.open(p.resolve().as_uri())
    print(f"Opened {p}")


@app.command("export-reports")
def export_reports(
    reports_dir: str = typer.Option("reports", help="Reports directory"),
    out_zip: str = typer.Option("reports/export.zip", help="Output zip path"),
):
    """Zip all files under the reports directory for sharing."""
    r = Path(reports_dir)
    if not r.exists():
        print(f"[red]Directory not found:[/red] {r}")
        raise typer.Exit(code=2)
    out = Path(out_zip)
    ensure_dir(out.parent)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in r.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(r))
    print(f"[green]Exported[/green] {out}")


@app.command("plan-run")
def plan_run(
    quick: bool = typer.Option(True, help="Quick run: a11y+LH+perf short; skip UI unless tests exist"),
    html_report: bool = typer.Option(True, help="Write HTML findings report"),
):
    """Simple end-to-end plan: detect -> run tools -> generate report."""
    # Detect OpenAPI + base_url
    cfg = load_config()
    openapi = (cfg.api.openapi if cfg and cfg.api.openapi else None) or (
        find_openapi_candidates(Path.cwd())[0].as_posix() if find_openapi_candidates(Path.cwd()) else None
    )
    base_url = (cfg.api.base_url if cfg and cfg.api.base_url else None) or os.environ.get("BASE_URL")

    # API
    if openapi and base_url:
        print("[cyan]Running Schemathesis...[/cyan]")
        try:
            schemathesis_run.callback(openapi=openapi, base_url=base_url)  # type: ignore[attr-defined]
        except SystemExit:
            pass
    else:
        print("[yellow]Skipping Schemathesis (spec or base_url missing)[/yellow]")

    # UI
    ui_dir = Path("tests/ui")
    if ui_dir.exists() and any(ui_dir.glob("test_*.py")):
        print("[cyan]Running UI tests...[/cyan]")
        try:
            ui_run.callback(path=str(ui_dir), base_url=base_url)  # type: ignore[attr-defined]
        except SystemExit:
            pass
    else:
        print("[yellow]Skipping UI (no tests found)[/yellow]")

    # A11y + Lighthouse
    if base_url:
        try:
            a11y_run.callback(url=[base_url])  # type: ignore[attr-defined]
        except SystemExit:
            pass
        try:
            lighthouse_audit.callback(url=base_url)  # type: ignore[attr-defined]
        except SystemExit:
            pass
    else:
        print("[yellow]Skipping a11y / Lighthouse (no BASE_URL)[/yellow]")

    # Perf (short)
    if base_url:
        try:
            perf_run.callback(users=5, spawn_rate=2.0, run_time="15s")  # type: ignore[attr-defined]
        except SystemExit:
            pass

    # Report
    fmt = "html" if html_report else "markdown"
    out = "reports/findings.html" if html_report else "reports/findings.md"
    result = generate_report(output=out, fmt=fmt)
    print(f"[green]Findings written:[/green] {result['output']}")



def main():
    app()
