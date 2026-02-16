"""Analyze subcommands for the qaagent CLI."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import click
import typer
from rich import print
from rich.table import Table

from ._helpers import (
    console,
    detect_stack,
    load_risks_from_file,
    load_routes_from_file,
    print_routes_table,
)
from .analyze import run_collectors, ensure_risks, ensure_recommendations
from qaagent.analyzers.route_coverage import build_route_coverage
from qaagent.analyzers.models import Risk, Route
from qaagent.analyzers.dom_analyzer import run_dom_analysis
from qaagent.analyzers.risk_assessment import assess_risks
from qaagent.analyzers.route_discovery import discover_routes, discover_from_source, export_routes
from qaagent.analyzers.strategy_generator import build_strategy_summary, export_strategy
from qaagent.config import load_active_profile


class _AnalyzeGroup(typer.core.TyperGroup):
    """Custom Click group that falls back to the 'repo' subcommand for
    unrecognized tokens, so ``qaagent analyze .`` works alongside
    ``qaagent analyze routes``."""

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            # Unrecognized token (e.g. ".") - redirect to 'repo' subcommand
            default = self.get_command(ctx, "repo")
            if default is not None:
                return "repo", default, args
            raise


analyze_app = typer.Typer(
    help="Intelligent analysis commands",
    cls=_AnalyzeGroup,
    invoke_without_command=True,
    no_args_is_help=False,
)


def analyze_repo(path: str = "."):
    """Heuristic repo analysis to propose a QA plan."""
    root = Path(path).resolve()
    if not root.exists():
        typer.echo(f"Path not found: {root}")
        raise typer.Exit(code=2)

    summary = detect_stack(root)

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


def _default_junit_files(root: Path) -> List[Path]:
    candidates = [
        root / "reports" / "pytest" / "junit.xml",
        root / "reports" / "schemathesis" / "junit.xml",
        root / "reports" / "ui" / "junit.xml",
    ]
    return [path for path in candidates if path.exists()]


def _resolve_junit_files(
    junit_inputs: Optional[List[str]],
    search_root: Path,
) -> List[Path]:
    files: List[Path] = []

    if junit_inputs:
        for raw in junit_inputs:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = (Path.cwd() / path).resolve()
            if not path.exists():
                continue
            if path.is_dir():
                files.extend(sorted(path.glob("*.xml")))
            else:
                files.append(path)
    else:
        files.extend(_default_junit_files(search_root))

    deduped: List[Path] = []
    seen = set()
    for path in files:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _render_coverage_markdown(summary: dict) -> str:
    lines = [
        "# Route Coverage Gaps",
        "",
        f"- Spec: {summary.get('spec') or 'N/A'}",
        f"- Covered operations: {summary.get('covered', 0)}/{summary.get('total', 0)} ({summary.get('pct', 0)}%)",
        "",
        "## Top Uncovered Routes",
    ]
    uncovered = summary.get("uncovered", []) or []
    if not uncovered:
        lines.append("- None")
        return "\n".join(lines)

    for item in uncovered[:20]:
        lines.append(
            f"- `{item.get('priority', 'low')}` {item.get('method')} {item.get('path')} ({item.get('priority_reason')})",
        )
    return "\n".join(lines)


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


@analyze_app.callback()
def analyze_callback(ctx: typer.Context):
    """Heuristic repo analysis to propose a QA plan."""
    if ctx.invoked_subcommand is None:
        analyze_repo(".")


@analyze_app.command("repo")
def analyze_repo_cmd(path: str = typer.Argument(".", help="Project root to analyze")):
    """Heuristic repo analysis to propose a QA plan."""
    analyze_repo(path)


@analyze_app.command("collectors")
def analyze_collectors_command(
    target: Path = typer.Argument(Path.cwd(), help="Target repository directory"),
    runs_dir: Optional[Path] = typer.Option(None, "--runs-dir", help="Override runs directory"),
):
    """Execute the new collector pipeline and persist evidence."""
    try:
        run_id = run_collectors(target, runs_dir)
        typer.echo(f"Run completed: {run_id}")
    except FileNotFoundError as exc:
        typer.echo(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2)


@analyze_app.command("routes")
def analyze_routes(
    openapi: Optional[str] = typer.Option(None, help="Path or URL to OpenAPI/Swagger spec"),
    target: Optional[str] = typer.Option(None, help="Base URL to probe (future enhancement)"),
    source: Optional[str] = typer.Option(None, "--source", "--source-dir", help="Path to source code for static analysis"),
    out: str = typer.Option("routes.json", help="Output file for discovered routes"),
    format: str = typer.Option("json", help="Output format: json|yaml|table"),
    verbose: bool = typer.Option(False, "--verbose", help="Include additional metadata when printing"),
    crawl: bool = typer.Option(False, "--crawl", help="Discover runtime routes by crawling UI navigation links"),
    crawl_url: Optional[str] = typer.Option(None, "--crawl-url", help="Starting URL for runtime crawl"),
    crawl_depth: int = typer.Option(2, "--crawl-depth", min=0, help="Max crawl depth from starting URL"),
    crawl_max_pages: int = typer.Option(50, "--crawl-max-pages", min=1, help="Max pages to crawl"),
    crawl_same_origin: bool = typer.Option(
        True,
        "--crawl-same-origin/--crawl-allow-external",
        help="Restrict crawl to the same origin as crawl URL",
    ),
    crawl_timeout: float = typer.Option(20.0, "--crawl-timeout", min=0.1, help="Page navigation timeout (seconds)"),
    crawl_wait_until: str = typer.Option(
        "networkidle",
        "--crawl-wait-until",
        help="Navigation ready state: load|domcontentloaded|networkidle|commit",
    ),
    crawl_browser: str = typer.Option("chromium", "--crawl-browser", help="Browser engine: chromium|firefox|webkit"),
    crawl_headed: bool = typer.Option(False, "--crawl-headed", help="Run crawler in headed mode"),
    crawl_storage_state: Optional[str] = typer.Option(
        None,
        "--crawl-storage-state",
        help="Optional Playwright storage state JSON path for authenticated crawl session",
    ),
    crawl_header: Optional[List[str]] = typer.Option(
        None,
        "--crawl-header",
        help="Extra crawl request header KEY:VALUE (repeatable)",
    ),
    crawl_auth_header: Optional[str] = typer.Option(
        None,
        "--crawl-auth-header",
        help="Auth header name for crawl requests (defaults from profile)",
    ),
    crawl_auth_token_env: Optional[str] = typer.Option(
        None,
        "--crawl-auth-token-env",
        help="Env var containing auth token for crawl requests",
    ),
    crawl_auth_prefix: str = typer.Option(
        "Bearer ",
        "--crawl-auth-prefix",
        help="Prefix for crawl auth token header value",
    ),
):
    """Discover API and UI routes from available inputs."""
    active_entry = None
    active_profile = None
    project_root = Path.cwd()
    if not any([openapi, target, source]) or crawl:
        try:
            active_entry, active_profile = load_active_profile()
        except Exception:
            pass
        else:
            project_root = active_entry.resolved_path()
            spec_path = active_profile.resolve_spec_path(project_root)
            if spec_path and spec_path.exists():
                openapi = spec_path.as_posix()
            source_dir = active_profile.openapi.source_dir
            if source_dir:
                candidate = project_root / source_dir
                if candidate.exists():
                    source = str(candidate)
            dev_env = active_profile.app.get("dev") if active_profile.app else None
            if dev_env and dev_env.base_url:
                target = target or dev_env.base_url

    effective_crawl_url = crawl_url or target
    if not any([openapi, target, source]) and not crawl:
        typer.echo(
            "Provide at least one discovery source (e.g., --openapi path/to/openapi.yaml) or set an active target."
        )
        raise typer.Exit(code=2)
    if crawl and not effective_crawl_url:
        typer.echo("Crawl enabled but no URL available. Provide --crawl-url, --target, or configure app.dev.base_url.")
        raise typer.Exit(code=2)

    crawl_headers: Dict[str, str] = {}
    crawl_storage_state_path: Optional[Path] = None

    if crawl:
        env = _pick_profile_environment(active_profile) if active_profile else None

        try:
            crawl_headers = _parse_extra_headers(crawl_header)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2)

        if env and env.headers:
            merged = dict(env.headers)
            merged.update(crawl_headers)
            crawl_headers = merged

        if env and env.auth:
            crawl_auth_header = crawl_auth_header or env.auth.header_name
            crawl_auth_token_env = crawl_auth_token_env or env.auth.token_env
            if crawl_auth_prefix == "Bearer " and env.auth.prefix:
                crawl_auth_prefix = env.auth.prefix

        if crawl_auth_token_env:
            token = os.environ.get(crawl_auth_token_env)
            if token:
                header_name = crawl_auth_header or "Authorization"
                crawl_headers[header_name] = f"{crawl_auth_prefix}{token}" if crawl_auth_prefix else token
            elif crawl_auth_header:
                console.print(
                    f"[yellow]Crawl token env '{crawl_auth_token_env}' is unset; continuing without {crawl_auth_header} header.[/yellow]"
                )

        if crawl_storage_state:
            crawl_storage_state_path = Path(crawl_storage_state)
        elif env and active_profile and active_profile.tests.e2e and active_profile.tests.e2e.auth_setup:
            candidate = project_root / ".auth" / "state.json"
            if candidate.exists():
                crawl_storage_state_path = candidate

    routes = discover_routes(
        target=target,
        openapi_path=openapi,
        source_path=source,
        crawl=crawl,
        crawl_url=effective_crawl_url,
        crawl_depth=crawl_depth,
        crawl_max_pages=crawl_max_pages,
        crawl_same_origin=crawl_same_origin,
        crawl_timeout_seconds=crawl_timeout,
        crawl_wait_until=crawl_wait_until,
        crawl_browser=crawl_browser,
        crawl_headless=not crawl_headed,
        crawl_headers=crawl_headers or None,
        crawl_storage_state_path=crawl_storage_state_path,
    )
    if not routes:
        print("[yellow]No routes discovered.[/yellow]")

    fmt = format.lower()
    out_path = Path(out)

    if fmt == "table":
        print_routes_table(routes, verbose=verbose)
        if out:
            export_routes(routes, out_path, "json")
            print(f"[green]Discovered {len(routes)} routes -> {out_path}[/green]")
    else:
        export_routes(routes, out_path, fmt)
        print(f"[green]Discovered {len(routes)} routes -> {out_path}[/green]")
        if verbose:
            print_routes_table(routes, verbose=True)


@analyze_app.command("dom")
def analyze_dom(
    url: Optional[str] = typer.Option(None, "--url", help="Page URL to inspect (falls back to active target base_url)"),
    out: str = typer.Option("dom-analysis.json", "--out", help="Output JSON path"),
    browser: str = typer.Option("chromium", help="Browser engine: chromium|firefox|webkit"),
    timeout: float = typer.Option(30.0, "--timeout", help="Navigation timeout in seconds"),
    wait_until: str = typer.Option(
        "networkidle",
        "--wait-until",
        help="Navigation ready state: load|domcontentloaded|networkidle|commit",
    ),
    headed: bool = typer.Option(False, "--headed", help="Run browser headed (default is headless)"),
    include_external_links: bool = typer.Option(
        False,
        "--include-external-links",
        help="Include external links in nav-link inventory",
    ),
    max_links: int = typer.Option(200, "--max-links", min=1, help="Max nav links to include in output"),
    storage_state: Optional[str] = typer.Option(
        None,
        "--storage-state",
        help="Optional Playwright storage state JSON path for authenticated sessions",
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
):
    """Inspect live DOM with Playwright and generate selector strategy guidance."""
    active_entry = None
    active_profile = None
    project_root = Path.cwd()

    if not url or not auth_token_env or not auth_header or storage_state is None:
        try:
            active_entry, active_profile = load_active_profile()
        except Exception:
            active_entry = None
            active_profile = None
        else:
            project_root = active_entry.resolved_path()

    env = _pick_profile_environment(active_profile) if active_profile else None
    if env:
        if not url and env.base_url:
            url = env.base_url
        if env.auth:
            auth_header = auth_header or env.auth.header_name
            auth_token_env = auth_token_env or env.auth.token_env
            if auth_prefix == "Bearer " and env.auth.prefix:
                auth_prefix = env.auth.prefix

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

    try:
        analysis = run_dom_analysis(
            url=url,
            out_path=Path(out),
            browser=browser,
            timeout_seconds=timeout,
            wait_until=wait_until,
            headless=not headed,
            headers=headers or None,
            storage_state_path=storage_state_path,
            include_external_links=include_external_links,
            max_links=max_links,
        )
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Failed to analyze DOM: {exc}")
        raise typer.Exit(code=2)

    summary = analysis.get("summary", {}) if isinstance(analysis, dict) else {}
    table = Table(title="DOM Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Pages", str(summary.get("pages_analyzed", 0)))
    table.add_row("Elements", str(summary.get("elements_total", 0)))
    table.add_row("Interactive", str(summary.get("interactive_elements", 0)))
    table.add_row("Forms", str(summary.get("forms_total", 0)))
    selector = summary.get("selector_strategy", {}) if isinstance(summary, dict) else {}
    table.add_row("Stable selector coverage", f"{selector.get('stable_selector_coverage_pct', 0)}%")
    table.add_row("data-testid coverage", f"{selector.get('testid_coverage_pct', 0)}%")
    table.add_row("ARIA coverage", f"{selector.get('aria_coverage_pct', 0)}%")
    console.print(table)

    recommendations = analysis.get("recommendations", []) if isinstance(analysis, dict) else []
    if recommendations:
        console.print("[bold]Recommendations[/bold]")
        for idx, item in enumerate(recommendations, start=1):
            console.print(f"{idx}. {item}")

    console.print(f"[green]DOM analysis written → {Path(out)}[/green]")


@analyze_app.command("coverage-gaps")
def analyze_coverage_gaps(
    routes_file: Optional[str] = typer.Option(None, "--routes-file", help="Path to routes.json/yaml"),
    openapi: Optional[str] = typer.Option(None, help="Path or URL to OpenAPI/Swagger spec"),
    junit: Optional[List[str]] = typer.Option(
        None,
        "--junit",
        help="JUnit XML file or directory (repeatable)",
    ),
    out: Optional[str] = typer.Option(None, "--out", help="Optional JSON output path"),
    markdown: Optional[str] = typer.Option(None, "--markdown", help="Optional markdown summary output path"),
):
    """Analyze route-level coverage gaps from OpenAPI/routes and JUnit artifacts."""
    active_entry = None
    active_profile = None
    search_root = Path.cwd()
    routes: Optional[List[Route]] = None

    if routes_file:
        routes_path = Path(routes_file)
        if not routes_path.exists():
            typer.echo(f"Routes file not found: {routes_path}")
            raise typer.Exit(code=2)
        routes = load_routes_from_file(routes_path)

    if not openapi and routes is None:
        try:
            active_entry, active_profile = load_active_profile()
        except Exception:
            active_entry = None
            active_profile = None
        else:
            search_root = active_entry.resolved_path()
            spec_path = active_profile.resolve_spec_path(search_root)
            if spec_path and spec_path.exists():
                openapi = spec_path.as_posix()

    if not openapi and routes is None:
        typer.echo("Provide --routes-file or --openapi, or configure an active target with openapi.spec_path.")
        raise typer.Exit(code=2)

    junit_files = _resolve_junit_files(junit, search_root)
    if not junit_files:
        typer.echo("No JUnit files found. Provide --junit or generate reports first.")
        raise typer.Exit(code=2)

    try:
        summary = build_route_coverage(
            openapi_path=openapi,
            routes=routes,
            junit_files=junit_files,
        )
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Failed to analyze coverage gaps: {exc}")
        raise typer.Exit(code=2)

    if not summary:
        typer.echo("No operations available for coverage analysis.")
        raise typer.Exit(code=2)

    table = Table(title="Route Coverage Gaps")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Spec", str(summary.get("spec") or "N/A"))
    table.add_row(
        "Coverage",
        f"{summary.get('covered', 0)}/{summary.get('total', 0)} ({summary.get('pct', 0)}%)",
    )
    table.add_row("Uncovered", str(len(summary.get("uncovered", []))))
    console.print(table)

    uncovered = summary.get("uncovered", []) or []
    if uncovered:
        gaps = Table(title="Top Uncovered Routes")
        gaps.add_column("Priority", style="magenta")
        gaps.add_column("Method", style="cyan")
        gaps.add_column("Path", style="white")
        gaps.add_column("Reason", style="green")
        for item in uncovered[:15]:
            gaps.add_row(
                str(item.get("priority", "low")),
                str(item.get("method", "")),
                str(item.get("path", "")),
                str(item.get("priority_reason", "")),
            )
        console.print(gaps)

    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        console.print(f"[green]Coverage gaps exported → {out_path}[/green]")

    if markdown:
        md_path = Path(markdown)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_render_coverage_markdown(summary), encoding="utf-8")
        console.print(f"[green]Coverage markdown written → {md_path}[/green]")


@analyze_app.command("risks")
def analyze_risks_command(
    run: Optional[str] = typer.Argument(None, help="Run ID or path (defaults to latest)"),
    runs_dir: Optional[Path] = typer.Option(None, "--runs-dir", help="Runs directory"),
    config: Path = typer.Option(Path("handoff/risk_config.yaml"), "--config", help="Risk config path"),
    top: int = typer.Option(10, "--top", help="Number of risks to display"),
    json_out: Optional[Path] = typer.Option(None, "--json-out", help="Optional JSON export"),
):
    """Display risk scores aggregated from collected evidence."""
    try:
        handle, risks = ensure_risks(run, runs_dir, config)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)

    if not risks:
        console.print("[yellow]No risks available. Run collectors first.[/yellow]")
        return

    sorted_risks = sorted(risks, key=lambda r: r.score, reverse=True)
    table = Table(title=f"Risk Summary ({handle.run_id})")
    table.add_column("Component", style="cyan")
    table.add_column("Score", style="magenta")
    table.add_column("Band", style="green")
    table.add_column("Severity", style="red")
    table.add_column("Confidence", style="blue")

    for risk in sorted_risks[:top]:
        table.add_row(
            risk.component,
            f"{risk.score:.1f}",
            risk.band,
            risk.severity,
            f"{risk.confidence:.0%}",
        )

    console.print(table)
    console.print(f"Risks stored at {(handle.evidence_dir / 'risks.jsonl').as_posix()}")

    if json_out:
        json_out.write_text(json.dumps([risk.to_dict() for risk in sorted_risks], indent=2), encoding="utf-8")
        console.print(f"Exported risks -> {json_out}")


@analyze_app.command("recommendations")
def analyze_recommendations_command(
    run: Optional[str] = typer.Argument(None, help="Run ID or path (defaults to latest)"),
    runs_dir: Optional[Path] = typer.Option(None, "--runs-dir", help="Runs directory"),
    risk_config: Path = typer.Option(Path("handoff/risk_config.yaml"), "--risk-config", help="Risk config path"),
    cuj_config: Path = typer.Option(Path("handoff/cuj.yaml"), "--cuj-config", help="CUJ config path"),
    top: int = typer.Option(10, "--top", help="Number of recommendations to display"),
    json_out: Optional[Path] = typer.Option(None, "--json-out", help="Optional JSON export"),
):
    """Display testing recommendations based on risks and CUJ coverage."""
    try:
        handle, risks, recs = ensure_recommendations(run, runs_dir, risk_config, cuj_config)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)

    if not recs:
        console.print("[yellow]No recommendations available. Ensure coverage data exists.[/yellow]")
        return

    priority_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    sorted_recs = sorted(recs, key=lambda r: priority_order.get(r.priority.lower(), 0), reverse=True)

    table = Table(title=f"Recommendations ({handle.run_id})")
    table.add_column("Component", style="cyan")
    table.add_column("Priority", style="magenta")
    table.add_column("Summary", style="white")

    for rec in sorted_recs[:top]:
        table.add_row(rec.component, rec.priority, rec.summary)

    console.print(table)
    console.print(f"Recommendations stored at {(handle.evidence_dir / 'recommendations.jsonl').as_posix()}")

    if json_out:
        json_out.write_text(json.dumps([rec.to_dict() for rec in sorted_recs], indent=2), encoding="utf-8")
        console.print(f"Exported recommendations -> {json_out}")


@analyze_app.command("strategy")
def analyze_strategy(
    routes_file: Optional[str] = typer.Option(None, help="routes.json generated by analyze routes"),
    risks_file: Optional[str] = typer.Option(None, help="risks.json generated by analyze risks"),
    openapi: Optional[str] = typer.Option(None, help="Fallback OpenAPI spec if routes file not provided"),
    out: str = typer.Option("strategy.yaml", help="Path to YAML strategy output"),
    markdown: Optional[str] = typer.Option("strategy.md", help="Optional Markdown export"),
):
    """Generate testing strategy recommendations based on discovered routes and risks."""
    # Load active profile up front (best-effort) so disabled_rules is
    # available regardless of how routes are sourced.
    active_entry = None
    active_profile = None
    try:
        active_entry, active_profile = load_active_profile()
    except Exception:
        pass

    if routes_file:
        routes = load_routes_from_file(Path(routes_file))
    elif openapi:
        routes = discover_routes(openapi_path=openapi)
    elif active_entry and active_profile:
        project_root = active_entry.resolved_path()
        spec_path = active_profile.resolve_spec_path(project_root)
        if spec_path and spec_path.exists():
            routes = discover_routes(openapi_path=str(spec_path))
        else:
            typer.echo("Active target does not define an OpenAPI spec path.")
            raise typer.Exit(code=2)
    else:
        typer.echo("Provide --routes-file FILE or --openapi SPEC to generate strategy or set an active target.")
        raise typer.Exit(code=2)

    if risks_file:
        risks = load_risks_from_file(Path(risks_file))
    else:
        risk_kwargs: dict = {}
        if active_profile:
            ra = active_profile.risk_assessment
            if ra.disable_rules:
                risk_kwargs["disabled_rules"] = set(ra.disable_rules)
            if ra.custom_rules:
                risk_kwargs["custom_rules"] = ra.custom_rules
            if ra.custom_rules_file:
                root = active_entry.resolved_path() if active_entry else Path.cwd()
                resolved = active_profile.resolve_custom_rules_path(root)
                if resolved:
                    risk_kwargs["custom_rules_file"] = resolved
            if ra.severity_overrides:
                risk_kwargs["severity_overrides"] = ra.severity_overrides
        risks = assess_risks(routes, **risk_kwargs)

    summary = build_strategy_summary(routes, risks)

    markdown_path = Path(markdown) if markdown else None
    export_strategy(summary, Path(out), markdown_path)

    extra = f" and {markdown_path.as_posix()}" if markdown_path else ""
    print(f"[green]Strategy generated -> {out}{extra}[/green]")
