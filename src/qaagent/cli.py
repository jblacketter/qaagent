from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import importlib.util
from typing import Dict, Iterable, List, Optional

import typer
from pydantic import BaseModel
from rich import print
from rich.console import Console
from rich.table import Table

from .tools import ensure_dir, run_command, which
from . import __version__
from .report import generate_report
from .config import (
    load_config,
    write_default_config,
    write_env_example,
    TargetManager,
    load_active_profile,
    load_profile,
    TemplateContext,
    available_templates,
    render_template,
    find_config_file,
    CONFIG_FILENAME,
)
from .config.detect import (
    detect_project_type,
    default_base_url,
    default_start_command,
    default_spec_path,
    default_source_dir,
)
from .generators.behave_generator import BehaveGenerator
from .generators.unit_test_generator import UnitTestGenerator
from .generators.data_generator import DataGenerator
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
from .doctor import HealthStatus, checks_to_json, run_health_checks
from .analyzers.route_discovery import discover_routes, export_routes
from .analyzers.risk_assessment import assess_risks, export_risks_json, export_risks_markdown
from .analyzers.strategy_generator import build_strategy_summary, export_strategy
from .analyzers.models import Risk, RiskCategory, RiskSeverity, Route


app = typer.Typer(help="QA Agent CLI: analyze, test, and expose tools via MCP")
console = Console()
analyze_app = typer.Typer(help="Intelligent analysis commands")
app.add_typer(analyze_app, name="analyze")
config_app = typer.Typer(help="Manage QA Agent configuration profiles")
targets_app = typer.Typer(help="Manage registered QA Agent targets")
generate_app = typer.Typer(help="Generate tests and fixtures")
app.add_typer(config_app, name="config")
app.add_typer(targets_app, name="targets")
config_app.add_typer(targets_app, name="targets")
app.add_typer(generate_app, name="generate")


class AnalyzeSummary(BaseModel):
    root: str
    language_hints: list[str]
    frameworks: list[str]
    detected: list[str]
    recommendations: list[str]


def _load_json_or_yaml(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore

            return yaml.safe_load(text) or {}
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "PyYAML is required to parse YAML files. Install API extras: pip install -e .[api]"
            ) from exc
    return json.loads(text or "{}")


def _load_routes_from_file(path: Path) -> List[Route]:
    payload = _load_json_or_yaml(path)
    data: Iterable = payload.get("routes", payload) if isinstance(payload, dict) else payload
    return [Route.from_dict(item) for item in data]


def _load_risks_from_file(path: Path) -> List[Risk]:
    payload = _load_json_or_yaml(path)
    data: Iterable = payload.get("risks", payload) if isinstance(payload, dict) else payload
    risks: List[Risk] = []
    for item in data:
        category_value = item.get("category", RiskCategory.SECURITY.value)
        severity_value = item.get("severity", RiskSeverity.MEDIUM.value)
        try:
            category = RiskCategory(category_value)
        except ValueError:
            category = RiskCategory.SECURITY
        try:
            severity = RiskSeverity(severity_value)
        except ValueError:
            severity = RiskSeverity.MEDIUM
        risks.append(
            Risk(
                category=category,
                severity=severity,
                route=item.get("route"),
                title=item.get("title", ""),
                description=item.get("description", ""),
                recommendation=item.get("recommendation", ""),
                source=item.get("source", "file"),
                cwe_id=item.get("cwe_id"),
                owasp_top_10=item.get("owasp_top_10"),
                references=item.get("references", []),
                metadata=item.get("metadata", {}),
            )
        )
    return risks


def _print_routes_table(routes: List[Route], verbose: bool = False) -> None:
    table = Table(title=f"Discovered Routes ({len(routes)})", show_lines=False)
    table.add_column("Method", style="cyan", no_wrap=True)
    table.add_column("Path", style="white")
    table.add_column("Auth", style="magenta", no_wrap=True)
    table.add_column("Source", style="green", no_wrap=True)
    if verbose:
        table.add_column("Tags", style="yellow")

    for route in routes:
        row = [route.method, route.path, "Yes" if route.auth_required else "No", route.source.value]
        if verbose:
            row.append(", ".join(route.tags) or "-")
        table.add_row(*row)

    console.print(table)


def _target_manager() -> TargetManager:
    return TargetManager()


def _resolve_project_path(path: Optional[str]) -> Path:
    if path:
        return Path(path).expanduser().resolve()
    return Path.cwd().resolve()


def _render_profile_template(project_path: Path, template_name: Optional[str]) -> tuple[str, str]:
    project_type = template_name or detect_project_type(project_path)
    templates = available_templates()
    template_key = project_type if project_type in templates else "generic"
    context = TemplateContext(
        project_name=project_path.name,
        project_type=project_type,
        base_url=default_base_url(project_type),
        start_command=default_start_command(project_type),
        health_endpoint="/api/health" if project_type == "nextjs" else "/health",
        spec_path=default_spec_path(project_type),
        source_dir=default_source_dir(project_type),
    )
    return render_template(template_key, context), project_type


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


def analyze_repo(path: str = typer.Argument(".", help="Project root to analyze")):
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


app.command("analyze")(analyze_repo)
analyze_app.command("repo")(analyze_repo)


@analyze_app.command("routes")
def analyze_routes(
    openapi: Optional[str] = typer.Option(None, help="Path or URL to OpenAPI/Swagger spec"),
    target: Optional[str] = typer.Option(None, help="Base URL to probe (future enhancement)"),
    source: Optional[str] = typer.Option(None, help="Path to source code for static analysis"),
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
        _print_routes_table(routes, verbose=verbose)
        if out:
            export_routes(routes, out_path, "json")
            print(f"[green]Discovered {len(routes)} routes → {out_path}[/green]")
    else:
        export_routes(routes, out_path, fmt)
        print(f"[green]Discovered {len(routes)} routes → {out_path}[/green]")
        if verbose:
            _print_routes_table(routes, verbose=True)


@analyze_app.command("risks")
def analyze_risks_command(
    routes_file: Optional[str] = typer.Option(None, help="Existing routes.json generated by analyze routes"),
    openapi: Optional[str] = typer.Option(None, help="Provide OpenAPI spec if routes file not available"),
    out: str = typer.Option("risks.json", help="JSON file to write identified risks"),
    markdown: Optional[str] = typer.Option("risks.md", help="Optional Markdown export"),
):
    """Assess security, performance, and reliability risks."""
    active_entry = None
    active_profile = None
    if routes_file:
        routes = _load_routes_from_file(Path(routes_file))
    elif openapi:
        routes = discover_routes(openapi_path=openapi)
    else:
        try:
            active_entry, active_profile = load_active_profile()
        except Exception:
            typer.echo("Provide --routes FILE or --openapi SPEC to assess risks or set an active target.")
            raise typer.Exit(code=2)
        else:
            project_root = active_entry.resolved_path()
            spec_path = active_profile.resolve_spec_path(project_root)
            if spec_path and spec_path.exists():
                routes = discover_routes(openapi_path=str(spec_path))
            else:
                typer.echo("Active target does not define an OpenAPI spec path.")
                raise typer.Exit(code=2)

    risks = assess_risks(routes)

    export_risks_json(risks, Path(out))
    if markdown:
        export_risks_markdown(risks, Path(markdown))

    print(f"[green]Identified {len(risks)} risks → {out}[/green]")


@analyze_app.command("strategy")
def analyze_strategy(
    routes_file: Optional[str] = typer.Option(None, help="routes.json generated by analyze routes"),
    risks_file: Optional[str] = typer.Option(None, help="risks.json generated by analyze risks"),
    openapi: Optional[str] = typer.Option(None, help="Fallback OpenAPI spec if routes file not provided"),
    out: str = typer.Option("strategy.yaml", help="Path to YAML strategy output"),
    markdown: Optional[str] = typer.Option("strategy.md", help="Optional Markdown export"),
):
    """Generate testing strategy recommendations based on discovered routes and risks."""
    active_entry = None
    active_profile = None
    if routes_file:
        routes = _load_routes_from_file(Path(routes_file))
    elif openapi:
        routes = discover_routes(openapi_path=openapi)
    else:
        try:
            active_entry, active_profile = load_active_profile()
        except Exception:
            typer.echo("Provide --routes FILE or --openapi SPEC to generate strategy or set an active target.")
            raise typer.Exit(code=2)
        else:
            project_root = active_entry.resolved_path()
            spec_path = active_profile.resolve_spec_path(project_root)
            if spec_path and spec_path.exists():
                routes = discover_routes(openapi_path=str(spec_path))
            else:
                typer.echo("Active target does not define an OpenAPI spec path.")
                raise typer.Exit(code=2)

    if risks_file:
        risks = _load_risks_from_file(Path(risks_file))
    else:
        risks = assess_risks(routes)

    summary = build_strategy_summary(routes, risks)

    markdown_path = Path(markdown) if markdown else None
    export_strategy(summary, Path(out), markdown_path)

    extra = f" and {markdown_path.as_posix()}" if markdown_path else ""
    print(f"[green]Strategy generated → {out}{extra}[/green]")


def _is_git_url(path_or_url: str) -> bool:
    """Check if a string is a Git repository URL."""
    if not path_or_url:
        return False
    return (
        path_or_url.startswith("https://")
        or path_or_url.startswith("http://")
        or path_or_url.startswith("git@")
    )


def _clone_repository(url: str) -> Path:
    """Clone a repository and return its local path."""
    try:
        from .repo.cloner import RepoCloner
        from .repo.cache import RepoCache

        print(f"[cyan]Cloning repository from {url}...[/cyan]")

        cloner = RepoCloner()
        cache = RepoCache()

        # Clone or use existing
        local_path = cloner.clone(url, depth=1)

        # Register in cache
        cache.register_clone(url, local_path)

        print(f"[green]✓[/green] Cloned to {local_path}")

        return local_path

    except Exception as e:
        print(f"[red]Failed to clone repository: {e}[/red]")
        raise typer.Exit(code=1)


@config_app.command("init")
def config_init(
    path: Optional[str] = typer.Argument(None, help="Path to project root or GitHub URL"),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Template to use (generic|fastapi|nextjs)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Target name to register (defaults to folder name)"),
    register: bool = typer.Option(True, help="Register target after creating config"),
    activate: bool = typer.Option(False, help="Activate target after registration"),
    force: bool = typer.Option(False, help="Overwrite existing configuration"),
    auto_discover: bool = typer.Option(False, "--auto-discover", help="Auto-discover Next.js routes from source"),
):
    # Check if path is a Git URL
    if path and _is_git_url(path):
        project_path = _clone_repository(path)
    else:
        project_path = _resolve_project_path(path)
    config_path = project_path / CONFIG_FILENAME

    if config_path.exists() and not force:
        print(
            f"[yellow]Configuration already exists at {config_path}. Use --force to overwrite.[/yellow]"
        )
        raise typer.Exit(code=1)

    template_key = template.lower() if template else None
    try:
        content, resolved_template = _render_profile_template(project_path, template_key)
    except ValueError as exc:  # unknown template
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    config_path.write_text(content, encoding="utf-8")
    print(f"[green]Created configuration:[/green] {config_path}")

    if register:
        manager = _target_manager()
        target_name = name or project_path.name
        try:
            entry = manager.add_target(target_name, str(project_path), project_type=resolved_template)
            print(f"[green]Registered target `{target_name}`[/green]")
            if activate:
                manager.set_active(target_name)
                print(f"[green]Activated target `{target_name}`[/green]")
        except (ValueError, FileNotFoundError) as exc:
            print(f"[yellow]{exc}[/yellow]")


@config_app.command("validate")
def config_validate(path: Optional[str] = typer.Option(None, help="Path within project to validate")):
    project_path = _resolve_project_path(path)
    config_file = find_config_file(project_path)
    if not config_file:
        print("[red]No .qaagent.yaml found. Run `qaagent config init` first.[/red]")
        raise typer.Exit(code=1)
    try:
        load_profile(config_file)
    except Exception as exc:  # noqa: BLE001
        print(f"[red]Validation failed:[/red] {exc}")
        raise typer.Exit(code=1)
    else:
        print(f"[green]Configuration valid:[/green] {config_file}")


@config_app.command("show")
def config_show(path: Optional[str] = typer.Option(None, help="Path within project to show config")):
    project_path = _resolve_project_path(path)
    config_file = find_config_file(project_path)
    if not config_file:
        print("[red]No .qaagent.yaml found. Run `qaagent config init` first.[/red]")
        raise typer.Exit(code=1)
    import yaml  # type: ignore

    profile = load_profile(config_file)
    print(f"[cyan]Configuration:[/cyan] {config_file}")
    console.print(yaml.safe_dump(profile.dict(), sort_keys=False))


@targets_app.command("list")
def targets_list() -> None:
    manager = _target_manager()
    registry = manager.registry
    entries = list(manager.list_targets())
    table = Table(title="Registered Targets", show_lines=False)
    table.add_column("Active", style="green", no_wrap=True)
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Type", style="magenta")

    for entry in entries:
        is_active = "★" if registry.active == entry.name else ""
        table.add_row(is_active, entry.name, entry.path, entry.project_type or "-")

    if not entries:
        print("[yellow]No targets registered. Use `qaagent config init` or `qaagent targets add`.[/yellow]")
        return

    console.print(table)


@targets_app.command("add")
def targets_add(
    name: str = typer.Argument(..., help="Name for the target"),
    path: str = typer.Argument(..., help="Path to the target project"),
    project_type: Optional[str] = typer.Option(None, "--type", help="Project type override"),
    activate: bool = typer.Option(False, help="Activate target after adding"),
):
    manager = _target_manager()
    resolved = Path(path).expanduser().resolve()
    detected_type = project_type or detect_project_type(resolved)
    try:
        entry = manager.add_target(name, str(resolved), project_type=detected_type)
        print(f"[green]Registered target `{name}` at {resolved}[/green]")
        if activate:
            manager.set_active(name)
            print(f"[green]Activated target `{name}`[/green]")
    except (ValueError, FileNotFoundError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


@targets_app.command("remove")
def targets_remove(name: str = typer.Argument(..., help="Target name")) -> None:
    manager = _target_manager()
    try:
        manager.remove_target(name)
        print(f"[green]Removed target `{name}`[/green]")
    except ValueError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


@app.command("use")
def use_target(name: str = typer.Argument(..., help="Target name to activate")) -> None:
    manager = _target_manager()
    try:
        entry = manager.set_active(name)
    except ValueError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    else:
        print(f"[green]Active target:[/green] {entry.name} → {entry.path}")


@generate_app.command("behave")
def generate_behave(
    out: Optional[str] = typer.Option(None, help="Output directory for Behave assets"),
    routes_file: Optional[str] = typer.Option(None, help="Existing routes JSON to reuse"),
    risks_file: Optional[str] = typer.Option(None, help="Existing risks JSON to reuse"),
    base_url: Optional[str] = typer.Option(None, help="Override base URL"),
):
    try:
        active_entry, active_profile = load_active_profile()
    except Exception:
        if not routes_file:
            console.print("[red]No active target configured. Use `qaagent use <target>` or provide --routes.[/red]")
            raise typer.Exit(code=2)
        project_root = Path.cwd()
        active_profile = None
        active_entry = None
    else:
        project_root = active_entry.resolved_path()

    output_dir = None
    if out:
        output_dir = Path(out)
        if not output_dir.is_absolute():
            output_dir = project_root / output_dir
    elif active_profile and active_profile.tests.behave:
        output_dir = project_root / active_profile.tests.behave.output_dir
    else:
        output_dir = project_root / "tests/qaagent/behave"

    output_dir.mkdir(parents=True, exist_ok=True)

    routes: List[Route]
    if routes_file:
        routes = _load_routes_from_file(Path(routes_file))
    else:
        spec_path = None
        if active_profile:
            spec_path = active_profile.resolve_spec_path(project_root)
        if spec_path and spec_path.exists():
            routes = discover_routes(openapi_path=str(spec_path))
        else:
            print("[red]Unable to determine OpenAPI spec. Provide --routes or configure spec_path in .qaagent.yaml.[/red]")
            raise typer.Exit(code=2)

    risks: List[Risk]
    if risks_file:
        risks = _load_risks_from_file(Path(risks_file))
    else:
        risks = assess_risks(routes)

    resolved_base_url = (
        base_url
        or (
            active_profile.app.get("dev").base_url
            if active_profile and "dev" in active_profile.app and active_profile.app["dev"].base_url
            else None
        )
        or default_base_url(detect_project_type(project_root))
    )

    generator = BehaveGenerator(
        routes=routes,
        risks=risks,
        output_dir=output_dir,
        base_url=resolved_base_url,
        project_name=active_profile.project.name if active_profile else project_root.name,
    )
    outputs = generator.generate()

    print(f"[green]Generated Behave assets in {output_dir}[/green]")
    for key, path in outputs.items():
        print(f"  - {key}: {path}")


@generate_app.command("unit-tests")
def generate_unit_tests(
    out: Optional[str] = typer.Option(None, help="Output directory for unit tests"),
    routes_file: Optional[str] = typer.Option(None, help="Existing routes JSON to reuse"),
    base_url: Optional[str] = typer.Option(None, help="Override base URL"),
):
    """Generate pytest unit tests from discovered routes."""
    try:
        active_entry, active_profile = load_active_profile()
    except Exception:
        if not routes_file:
            console.print("[red]No active target configured. Use `qaagent use <target>` or provide --routes-file.[/red]")
            raise typer.Exit(code=2)
        project_root = Path.cwd()
        active_profile = None
        active_entry = None
    else:
        project_root = active_entry.resolved_path()

    # Determine output directory
    output_dir = None
    if out:
        output_dir = Path(out)
        if not output_dir.is_absolute():
            output_dir = project_root / output_dir
    elif active_profile and active_profile.tests.unit:
        output_dir = project_root / active_profile.tests.unit.output_dir
    else:
        output_dir = project_root / "tests/qaagent/unit"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load or discover routes
    routes: List[Route]
    if routes_file:
        routes = _load_routes_from_file(Path(routes_file))
    else:
        spec_path = None
        if active_profile:
            spec_path = active_profile.resolve_spec_path(project_root)
        if spec_path and spec_path.exists():
            routes = discover_routes(openapi_path=str(spec_path))
        else:
            console.print("[red]Unable to determine OpenAPI spec. Provide --routes-file or configure spec_path in .qaagent.yaml.[/red]")
            raise typer.Exit(code=2)

    # Resolve base URL
    resolved_base_url = (
        base_url
        or (
            active_profile.app.get("dev").base_url
            if active_profile and "dev" in active_profile.app and active_profile.app["dev"].base_url
            else None
        )
        or default_base_url(detect_project_type(project_root))
    )

    # Generate unit tests
    generator = UnitTestGenerator(routes=routes, base_url=resolved_base_url)
    outputs = generator.generate(output_dir)

    console.print(f"[green]Generated unit tests in {output_dir}[/green]")
    for key, path in outputs.items():
        console.print(f"  - {key}: {path}")


@generate_app.command("test-data")
def generate_test_data(
    model: str = typer.Argument(..., help="Model name (e.g., Pet, User)"),
    count: int = typer.Option(10, help="Number of records to generate"),
    out: Optional[str] = typer.Option(None, help="Output file path"),
    format: str = typer.Option("json", help="Output format: json, yaml, csv"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducibility"),
    routes_file: Optional[str] = typer.Option(None, help="Existing routes JSON to extract schemas"),
):
    """Generate realistic test data fixtures from schemas."""
    try:
        active_entry, active_profile = load_active_profile()
    except Exception:
        if not routes_file:
            console.print("[red]No active target configured. Use `qaagent use <target>` or provide --routes-file.[/red]")
            raise typer.Exit(code=2)
        project_root = Path.cwd()
        active_profile = None
        active_entry = None
    else:
        project_root = active_entry.resolved_path()

    # Determine output file
    output_file = None
    if out:
        output_file = Path(out)
        if not output_file.is_absolute():
            output_file = project_root / output_file
    elif active_profile and active_profile.tests.data:
        output_dir = project_root / active_profile.tests.data.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{model.lower()}s.{format}"
    else:
        output_dir = project_root / "tests/qaagent/fixtures"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{model.lower()}s.{format}"

    # Load or discover routes
    routes: List[Route]
    if routes_file:
        routes = _load_routes_from_file(Path(routes_file))
    else:
        spec_path = None
        if active_profile:
            spec_path = active_profile.resolve_spec_path(project_root)
        if spec_path and spec_path.exists():
            routes = discover_routes(openapi_path=str(spec_path))
        else:
            console.print("[red]Unable to determine OpenAPI spec. Provide --routes-file or configure spec_path in .qaagent.yaml.[/red]")
            raise typer.Exit(code=2)

    # Generate test data
    generator = DataGenerator(routes=routes, seed=seed)
    records = generator.generate(model_name=model, count=count, output_format=format)
    generator.save(records, output_file, format=format)

    console.print(f"[green]Generated {count} {model} records → {output_file}[/green]")


@generate_app.command("openapi")
def generate_openapi(
    out: Optional[str] = typer.Option(None, help="Output file path for OpenAPI spec"),
    title: Optional[str] = typer.Option(None, help="API title"),
    version: str = typer.Option("1.0.0", help="API version"),
    description: Optional[str] = typer.Option(None, help="API description"),
    format: str = typer.Option("json", help="Output format: json or yaml"),
    auto_discover: bool = typer.Option(False, "--auto-discover", help="Auto-discover Next.js routes from source"),
    workspace: bool = typer.Option(True, "--workspace/--no-workspace", help="Use workspace directory (recommended)"),
):
    """Generate OpenAPI 3.0 specification from discovered routes."""
    import json
    import yaml
    from qaagent.openapi_gen import OpenAPIGenerator
    from qaagent.discovery import NextJsRouteDiscoverer
    from qaagent.workspace import Workspace

    try:
        active_entry, active_profile = load_active_profile()
    except Exception:
        console.print("[red]No active target configured. Use `qaagent use <target>` first.[/red]")
        raise typer.Exit(code=2)

    project_root = active_entry.resolved_path()
    target_name = active_entry.name

    # Determine output file
    output_file = None
    if out:
        output_file = Path(out)
        if not output_file.is_absolute():
            if workspace:
                # Relative to workspace
                ws = Workspace()
                output_file = ws.get_target_workspace(target_name) / output_file
            else:
                # Relative to project
                output_file = project_root / output_file
    else:
        if workspace:
            # Default to workspace
            ws = Workspace()
            output_file = ws.get_openapi_path(target_name, format=format)
        else:
            # Default to project root
            ext = "json" if format == "json" else "yaml"
            output_file = project_root / f"openapi.{ext}"

    # Discover routes
    routes: List[Route]
    if auto_discover:
        console.print("[cyan]Auto-discovering routes from Next.js source code...[/cyan]")
        discoverer = NextJsRouteDiscoverer(project_root)
        routes = discoverer.discover()
        console.print(f"[green]Discovered {len(routes)} routes[/green]")
    else:
        spec_path = None
        if active_profile:
            spec_path = active_profile.resolve_spec_path(project_root)
        if spec_path and spec_path.exists():
            routes = discover_routes(openapi_path=str(spec_path))
        else:
            console.print("[yellow]No OpenAPI spec found. Use --auto-discover for Next.js projects.[/yellow]")
            raise typer.Exit(code=2)

    # Determine API metadata
    api_title = title or (active_profile.project.name if active_profile else project_root.name)
    api_description = description or f"Auto-generated API specification for {api_title}"

    # Generate OpenAPI spec
    console.print("[cyan]Generating OpenAPI 3.0 specification...[/cyan]")
    generator = OpenAPIGenerator(
        routes=routes,
        title=api_title,
        version=version,
        description=api_description,
    )
    spec = generator.generate()

    # Save to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if format == "json":
        output_file.write_text(json.dumps(spec, indent=2))
    else:
        output_file.write_text(yaml.dump(spec, default_flow_style=False, sort_keys=False))

    console.print(f"[green]✓ OpenAPI spec generated → {output_file}[/green]")
    console.print(f"  Paths: {len(spec['paths'])}")
    console.print(f"  Schemas: {len(spec['components']['schemas'])}")

    if workspace:
        console.print(f"[yellow]  → Files in workspace (not in target project yet)[/yellow]")
        console.print(f"[yellow]  → Use 'qaagent workspace apply' to copy to target[/yellow]")


workspace_app = typer.Typer(help="Manage workspace for generated artifacts")
app.add_typer(workspace_app, name="workspace")


@workspace_app.command("show")
def workspace_show(
    target: Optional[str] = typer.Argument(None, help="Target name (uses active target if not specified)"),
):
    """Show workspace contents for a target."""
    from qaagent.workspace import Workspace

    # Get target name
    if target is None:
        try:
            active_entry, _ = load_active_profile()
            target = active_entry.name
        except Exception:
            console.print("[red]No active target. Specify target name or use `qaagent use <target>`[/red]")
            raise typer.Exit(code=2)

    ws = Workspace()
    info = ws.get_workspace_info(target)

    if not info["exists"]:
        console.print(f"[yellow]No workspace found for target '{target}'[/yellow]")
        return

    console.print(f"[cyan]Workspace for '{target}':[/cyan]")
    console.print(f"  Path: {info['path']}")
    console.print()

    if info.get("files"):
        console.print("[green]Generated Files:[/green]")
        for filename, file_info in info["files"].items():
            if filename.startswith("openapi."):
                size_kb = file_info["size"] / 1024
                console.print(f"  ✓ {filename} ({size_kb:.1f} KB)")
            elif filename == "tests":
                unit_count = file_info.get("unit", 0)
                behave_count = file_info.get("behave", 0)
                if unit_count > 0:
                    console.print(f"  ✓ tests/unit/ ({unit_count} files)")
                if behave_count > 0:
                    console.print(f"  ✓ tests/behave/ ({behave_count} files)")
            elif filename == "reports":
                console.print(f"  ✓ reports/ ({file_info} files)")
            elif filename == "fixtures":
                console.print(f"  ✓ fixtures/ ({file_info} files)")
    else:
        console.print("[yellow]  No files generated yet[/yellow]")


@workspace_app.command("list")
def workspace_list():
    """List all targets with workspaces."""
    from qaagent.workspace import Workspace

    ws = Workspace()
    targets = ws.list_targets()

    if not targets:
        console.print("[yellow]No workspaces found[/yellow]")
        return

    console.print(f"[cyan]Workspaces ({len(targets)} targets):[/cyan]")
    for target_name in sorted(targets):
        info = ws.get_workspace_info(target_name)
        file_count = sum(
            1 if not isinstance(v, dict) else sum(v.values())
            for v in info.get("files", {}).values()
        )
        console.print(f"  • {target_name} ({file_count} files)")


@workspace_app.command("clean")
def workspace_clean(
    target: Optional[str] = typer.Argument(None, help="Target name (uses active target if not specified)"),
    all: bool = typer.Option(False, "--all", help="Clean all workspaces"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clean workspace for a target."""
    from qaagent.workspace import Workspace

    ws = Workspace()

    if all:
        if not force:
            typer.confirm("Clean ALL workspaces?", abort=True)
        ws.clean_all()
        console.print("[green]✓ All workspaces cleaned[/green]")
        return

    # Get target name
    if target is None:
        try:
            active_entry, _ = load_active_profile()
            target = active_entry.name
        except Exception:
            console.print("[red]No active target. Specify target name or use --all[/red]")
            raise typer.Exit(code=2)

    if not force:
        typer.confirm(f"Clean workspace for '{target}'?", abort=True)

    ws.clean_target(target)
    console.print(f"[green]✓ Workspace cleaned for '{target}'[/green]")


@workspace_app.command("apply")
def workspace_apply(
    target: Optional[str] = typer.Argument(None, help="Target name (uses active target if not specified)"),
    pattern: str = typer.Option("*", help="File pattern to copy (e.g., 'openapi.*', 'tests/*')"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be copied without copying"),
):
    """Apply workspace files to target project."""
    from qaagent.workspace import Workspace

    # Get target info
    if target is None:
        try:
            active_entry, _ = load_active_profile()
            target = active_entry.name
            target_path = active_entry.resolved_path()
        except Exception:
            console.print("[red]No active target. Specify target name or use `qaagent use <target>`[/red]")
            raise typer.Exit(code=2)
    else:
        # Look up target path
        try:
            from qaagent.config.manager import TargetManager
            manager = TargetManager()
            entry = manager.get(target)
            if not entry:
                console.print(f"[red]Target '{target}' not found[/red]")
                raise typer.Exit(code=2)
            target_path = entry.resolved_path()
        except Exception as e:
            console.print(f"[red]Error loading target: {e}[/red]")
            raise typer.Exit(code=2)

    ws = Workspace()
    copied = ws.copy_to_target(target, target_path, pattern, dry_run=dry_run)

    if not copied:
        console.print(f"[yellow]No files matching '{pattern}' in workspace[/yellow]")
        return

    if dry_run:
        console.print(f"[cyan]Would copy {len(copied)} files:[/cyan]")
    else:
        console.print(f"[green]✓ Copied {len(copied)} files to target:[/green]")

    for src, dest in copied:
        rel_dest = dest.relative_to(target_path) if dest.is_relative_to(target_path) else dest
        console.print(f"  {src.name} → {rel_dest}")


@app.command("doctor")
def doctor(json_out: bool = typer.Option(False, help="Emit machine-readable JSON output")):
    """Run health checks to validate local QA Agent prerequisites."""
    checks = run_health_checks()
    exit_code = 0 if all(check.status is not HealthStatus.ERROR for check in checks) else 1

    if json_out:
        payload = {
            "checks": checks_to_json(checks),
            "platform": {
                "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "system": os.uname().sysname if hasattr(os, "uname") else os.name,
            },
        }
        print(json.dumps(payload, indent=2))
        raise typer.Exit(code=exit_code)

    table = Table(title="QA Agent Health Check", show_lines=False)
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="white", no_wrap=True)
    table.add_column("Details", style="white")
    table.add_column("Suggestion", style="magenta")

    def format_status(status: HealthStatus) -> str:
        if status is HealthStatus.OK:
            return "[green]OK[/green]"
        if status is HealthStatus.WARNING:
            return "[yellow]WARN[/yellow]"
        return "[red]ERROR[/red]"

    for check in checks:
        table.add_row(
            check.name,
            format_status(check.status),
            check.message,
            check.suggestion or "-",
        )
    console.print(table)

    errors = [c for c in checks if c.status is HealthStatus.ERROR]
    warnings = [c for c in checks if c.status is HealthStatus.WARNING and c not in errors]

    console.rule("Summary")
    if errors:
        print(f"[red]✗ {len(errors)} failing checks[/red]")
    elif warnings:
        print(f"[yellow]⚠ {len(warnings)} warnings[/yellow]")
    else:
        print("[green]✓ All checks passed[/green]")
    raise typer.Exit(code=exit_code)


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


@app.command("dashboard")
def dashboard(
    out: Optional[str] = typer.Option(None, help="Output path for dashboard HTML"),
    target: Optional[str] = typer.Argument(None, help="Target name (uses active target if not specified)"),
):
    """Generate interactive visual dashboard with risk analysis and test recommendations."""
    from qaagent.dashboard import generate_dashboard_from_workspace

    # Get target name
    if target is None:
        try:
            active_entry, _ = load_active_profile()
            target = active_entry.name
        except Exception:
            console.print("[red]No active target. Specify target name or use `qaagent use <target>`[/red]")
            raise typer.Exit(code=2)

    try:
        # Determine output path
        output_path = None
        if out:
            output_path = Path(out)
            if not output_path.is_absolute():
                output_path = Path.cwd() / output_path

        console.print(f"[cyan]Generating dashboard for '{target}'...[/cyan]")
        console.print("[cyan]  → Discovering routes...[/cyan]")
        console.print("[cyan]  → Assessing risks...[/cyan]")
        console.print("[cyan]  → Building recommendations...[/cyan]")

        dashboard_path = generate_dashboard_from_workspace(target, output_path)

        console.print(f"[green]✓ Dashboard generated → {dashboard_path}[/green]")
        console.print()
        console.print("[yellow]Open in browser:[/yellow]")
        console.print(f"  open {dashboard_path}")
        console.print()
        console.print("[yellow]Or use:[/yellow]")
        console.print(f"  qaagent open-report --path {dashboard_path}")

    except Exception as e:
        console.print(f"[red]Error generating dashboard: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("web-ui")
def web_ui(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8080, help="Port to bind to"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser automatically"),
):
    """Start the web UI server - graphical interface for QA Agent."""
    try:
        from qaagent.web_ui import start_web_ui

        console.print(f"[cyan]Starting QA Agent Web UI...[/cyan]")
        console.print(f"[green]→ Server: http://{host}:{port}[/green]")
        console.print()
        console.print("[yellow]Web UI Features:[/yellow]")
        console.print("  • Configure targets (local repos or GitHub URLs)")
        console.print("  • Discover routes from Next.js projects")
        console.print("  • Generate OpenAPI specifications")
        console.print("  • View interactive dashboards")
        console.print("  • Browse workspace files")
        console.print()
        console.print("[dim]Press Ctrl+C to stop the server[/dim]")
        console.print()

        if open_browser:
            import webbrowser
            import threading
            import time

            def open_browser_delayed():
                time.sleep(1.5)  # Wait for server to start
                webbrowser.open(f"http://{host}:{port}")

            threading.Thread(target=open_browser_delayed, daemon=True).start()

        start_web_ui(host=host, port=port)

    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]✓ Web UI server stopped[/yellow]")
    except ImportError as e:
        console.print(f"[red]Web UI dependencies not available: {e}[/red]")
        console.print("[yellow]Install UI extras: pip install -e .[ui][/yellow]")
        raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[red]Failed to start web UI: {e}[/red]")
        raise typer.Exit(code=1)


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
