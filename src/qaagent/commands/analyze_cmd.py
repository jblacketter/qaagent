"""Analyze subcommands for the qaagent CLI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

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
from qaagent.analyzers.models import Risk, Route
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
):
    """Discover API and UI routes from available inputs."""
    active_entry = None
    active_profile = None
    if not any([openapi, target, source]):
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

    if not any([openapi, target, source]):
        typer.echo(
            "Provide at least one discovery source (e.g., --openapi path/to/openapi.yaml) or set an active target."
        )
        raise typer.Exit(code=2)

    routes = discover_routes(target=target, openapi_path=openapi, source_path=source)
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
        disabled = set(active_profile.risk_assessment.disable_rules) if active_profile else None
        risks = assess_risks(routes, disabled_rules=disabled)

    summary = build_strategy_summary(routes, risks)

    markdown_path = Path(markdown) if markdown else None
    export_strategy(summary, Path(out), markdown_path)

    extra = f" and {markdown_path.as_posix()}" if markdown_path else ""
    print(f"[green]Strategy generated -> {out}{extra}[/green]")
