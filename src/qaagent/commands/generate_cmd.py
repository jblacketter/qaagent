"""Generate subcommands for the qaagent CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import typer
from rich import print

from ._helpers import console, load_risks_from_file, load_routes_from_file
from qaagent.analyzers.models import Risk, Route
from qaagent.analyzers.risk_assessment import assess_risks
from qaagent.analyzers.route_discovery import discover_routes
from qaagent.config import load_active_profile
from qaagent.config.detect import default_base_url, detect_project_type
from qaagent.config.models import LLMSettings
from qaagent.generators.base import GenerationResult
from qaagent.generators.behave_generator import BehaveGenerator
from qaagent.generators.unit_test_generator import UnitTestGenerator
from qaagent.generators.data_generator import DataGenerator

generate_app = typer.Typer(help="Generate tests and fixtures")


def _resolve_llm_settings(active_profile) -> Optional[LLMSettings]:
    """Extract LLM settings from active profile."""
    if active_profile and active_profile.llm and active_profile.llm.enabled:
        return active_profile.llm
    return None


def _resolve_disabled_rules(active_profile) -> Optional[set]:
    """Extract disabled rules from active profile."""
    if active_profile and active_profile.risk_assessment.disable_rules:
        return set(active_profile.risk_assessment.disable_rules)
    return None


def _print_generation_result(result, label: str) -> None:
    """Print a GenerationResult summary."""
    if isinstance(result, GenerationResult):
        console.print(f"  Tests: {result.stats.get('tests', 0)}")
        console.print(f"  Files: {result.stats.get('files', 0)}")
        if result.llm_used:
            console.print("  [cyan]LLM enhancement: enabled[/cyan]")
        if result.warnings:
            for w in result.warnings:
                console.print(f"  [yellow]Warning: {w}[/yellow]")


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
        routes = load_routes_from_file(Path(routes_file))
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
        risks = load_risks_from_file(Path(risks_file))
    else:
        risks = assess_risks(routes, disabled_rules=_resolve_disabled_rules(active_profile))

    resolved_base_url = (
        base_url
        or (
            active_profile.app.get("dev").base_url
            if active_profile and "dev" in active_profile.app and active_profile.app["dev"].base_url
            else None
        )
        or default_base_url(detect_project_type(project_root))
    )

    llm_settings = _resolve_llm_settings(active_profile)

    generator = BehaveGenerator(
        routes=routes,
        risks=risks,
        output_dir=output_dir,
        base_url=resolved_base_url,
        project_name=active_profile.project.name if active_profile else project_root.name,
        llm_settings=llm_settings,
    )
    result = generator.generate()

    print(f"[green]Generated Behave assets in {output_dir}[/green]")
    _print_generation_result(result, "Behave")
    for key, path in result.files.items():
        print(f"  - {key}: {path}")


@generate_app.command("unit-tests")
def generate_unit_tests(
    out: Optional[str] = typer.Option(None, help="Output directory for unit tests"),
    routes_file: Optional[str] = typer.Option(None, help="Existing routes JSON to reuse"),
    risks_file: Optional[str] = typer.Option(None, help="Existing risks JSON to reuse"),
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
        routes = load_routes_from_file(Path(routes_file))
    else:
        spec_path = None
        if active_profile:
            spec_path = active_profile.resolve_spec_path(project_root)
        if spec_path and spec_path.exists():
            routes = discover_routes(openapi_path=str(spec_path))
        else:
            console.print("[red]Unable to determine OpenAPI spec. Provide --routes-file or configure spec_path in .qaagent.yaml.[/red]")
            raise typer.Exit(code=2)

    # Load or assess risks
    risks: List[Risk]
    if risks_file:
        risks = load_risks_from_file(Path(risks_file))
    else:
        risks = assess_risks(routes, disabled_rules=_resolve_disabled_rules(active_profile))

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

    llm_settings = _resolve_llm_settings(active_profile)

    # Generate unit tests
    generator = UnitTestGenerator(
        routes=routes,
        base_url=resolved_base_url,
        risks=risks,
        output_dir=output_dir,
        project_name=active_profile.project.name if active_profile else project_root.name,
        llm_settings=llm_settings,
    )
    result = generator.generate(output_dir)

    console.print(f"[green]Generated unit tests in {output_dir}[/green]")
    _print_generation_result(result, "Unit tests")
    for key, path in result.files.items():
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
        routes = load_routes_from_file(Path(routes_file))
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

    console.print(f"[green]Generated {count} {model} records \u2192 {output_file}[/green]")


@generate_app.command("e2e")
def generate_e2e(
    out: Optional[str] = typer.Option(None, help="Output directory for Playwright project"),
    routes_file: Optional[str] = typer.Option(None, help="Existing routes JSON to reuse"),
    risks_file: Optional[str] = typer.Option(None, help="Existing risks JSON to reuse"),
    base_url: Optional[str] = typer.Option(None, help="Override base URL"),
    cuj_file: Optional[str] = typer.Option(None, help="CUJ YAML file for user journey tests"),
):
    """Generate Playwright TypeScript E2E tests from routes and CUJs."""
    from qaagent.analyzers.cuj_config import CUJConfig
    from qaagent.generators.playwright_generator import PlaywrightGenerator
    from qaagent.config.models import PlaywrightSuiteSettings

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
    elif active_profile and active_profile.tests.e2e:
        output_dir = project_root / active_profile.tests.e2e.output_dir
    else:
        output_dir = project_root / "tests/qaagent/e2e"

    # Load or discover routes
    routes: List[Route]
    if routes_file:
        routes = load_routes_from_file(Path(routes_file))
    else:
        spec_path = None
        if active_profile:
            spec_path = active_profile.resolve_spec_path(project_root)
        if spec_path and spec_path.exists():
            routes = discover_routes(openapi_path=str(spec_path))
        else:
            console.print("[red]Unable to determine OpenAPI spec. Provide --routes-file or configure spec_path in .qaagent.yaml.[/red]")
            raise typer.Exit(code=2)

    # Load or assess risks
    risks: List[Risk]
    if risks_file:
        risks = load_risks_from_file(Path(risks_file))
    else:
        risks = assess_risks(routes, disabled_rules=_resolve_disabled_rules(active_profile))

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

    # Load CUJs
    cujs = []
    cuj_path = cuj_file
    if not cuj_path and active_profile and active_profile.tests.e2e:
        e2e_settings = active_profile.tests.e2e
        if isinstance(e2e_settings, PlaywrightSuiteSettings) and e2e_settings.cuj_path:
            cuj_path = e2e_settings.cuj_path
    if not cuj_path:
        # Try default locations
        for candidate in ["handoff/cuj.yaml", "cuj.yaml"]:
            p = project_root / candidate
            if p.exists():
                cuj_path = str(p)
                break
    if cuj_path:
        p = Path(cuj_path)
        if not p.is_absolute():
            p = project_root / p
        if p.exists():
            config = CUJConfig.load(p)
            cujs = config.journeys

    # Determine auth and browser settings
    auth_config = None
    browsers = ["chromium"]
    if active_profile and active_profile.tests.e2e:
        e2e_settings = active_profile.tests.e2e
        if isinstance(e2e_settings, PlaywrightSuiteSettings):
            browsers = e2e_settings.browsers
            if e2e_settings.auth_setup and active_profile.app.get("dev") and active_profile.app["dev"].auth:
                auth_config = active_profile.app["dev"].auth

    llm_settings = _resolve_llm_settings(active_profile)

    generator = PlaywrightGenerator(
        routes=routes,
        risks=risks,
        output_dir=output_dir,
        base_url=resolved_base_url,
        project_name=active_profile.project.name if active_profile else project_root.name,
        llm_settings=llm_settings,
        cujs=cujs,
        auth_config=auth_config,
        browsers=browsers,
    )
    result = generator.generate()

    console.print(f"[green]Generated Playwright E2E project in {output_dir}[/green]")
    _print_generation_result(result, "E2E")
    for key, path in result.files.items():
        console.print(f"  - {key}: {path}")


@generate_app.command("all")
def generate_all(
    out: Optional[str] = typer.Option(None, help="Override base output directory"),
    routes_file: Optional[str] = typer.Option(None, help="Existing routes JSON to reuse"),
    risks_file: Optional[str] = typer.Option(None, help="Existing risks JSON to reuse"),
    base_url: Optional[str] = typer.Option(None, help="Override base URL"),
):
    """Generate all enabled test suites from .qaagent.yaml config."""
    from rich.table import Table
    from qaagent.generators.playwright_generator import PlaywrightGenerator
    from qaagent.analyzers.cuj_config import CUJConfig
    from qaagent.config.models import PlaywrightSuiteSettings

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

    # Load or discover routes
    routes: List[Route]
    if routes_file:
        routes = load_routes_from_file(Path(routes_file))
    else:
        spec_path = None
        if active_profile:
            spec_path = active_profile.resolve_spec_path(project_root)
        if spec_path and spec_path.exists():
            routes = discover_routes(openapi_path=str(spec_path))
        else:
            console.print("[red]Unable to determine OpenAPI spec. Provide --routes-file or configure spec_path in .qaagent.yaml.[/red]")
            raise typer.Exit(code=2)

    # Load or assess risks
    risks: List[Risk]
    if risks_file:
        risks = load_risks_from_file(Path(risks_file))
    else:
        risks = assess_risks(routes, disabled_rules=_resolve_disabled_rules(active_profile))

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

    llm_settings = _resolve_llm_settings(active_profile)
    tests_settings = active_profile.tests if active_profile else None
    results: Dict[str, GenerationResult] = {}

    # -- Unit tests --
    if tests_settings and tests_settings.unit and tests_settings.unit.enabled:
        unit_dir = Path(out) / "unit" if out else project_root / tests_settings.unit.output_dir
        unit_dir.mkdir(parents=True, exist_ok=True)
        gen = UnitTestGenerator(
            routes=routes, base_url=resolved_base_url, risks=risks,
            output_dir=unit_dir,
            project_name=active_profile.project.name if active_profile else project_root.name,
            llm_settings=llm_settings,
        )
        results["unit"] = gen.generate(unit_dir)
        console.print("[green]  Unit tests generated[/green]")
    else:
        console.print("[dim]  Unit tests: disabled[/dim]")

    # -- Behave --
    if tests_settings and tests_settings.behave and tests_settings.behave.enabled:
        behave_dir = Path(out) / "behave" if out else project_root / tests_settings.behave.output_dir
        behave_dir.mkdir(parents=True, exist_ok=True)
        gen = BehaveGenerator(
            routes=routes, risks=risks, output_dir=behave_dir,
            base_url=resolved_base_url,
            project_name=active_profile.project.name if active_profile else project_root.name,
            llm_settings=llm_settings,
        )
        results["behave"] = gen.generate()
        console.print("[green]  Behave features generated[/green]")
    else:
        console.print("[dim]  Behave: disabled[/dim]")

    # -- E2E (Playwright) --
    if tests_settings and tests_settings.e2e and tests_settings.e2e.enabled:
        e2e_dir = Path(out) / "e2e" if out else project_root / tests_settings.e2e.output_dir
        cujs = []
        e2e_settings = tests_settings.e2e
        if isinstance(e2e_settings, PlaywrightSuiteSettings) and e2e_settings.cuj_path:
            p = project_root / e2e_settings.cuj_path
            if p.exists():
                cujs = CUJConfig.load(p).journeys
        auth_config = None
        browsers = ["chromium"]
        if isinstance(e2e_settings, PlaywrightSuiteSettings):
            browsers = e2e_settings.browsers
            if e2e_settings.auth_setup and active_profile.app.get("dev") and active_profile.app["dev"].auth:
                auth_config = active_profile.app["dev"].auth
        gen = PlaywrightGenerator(
            routes=routes, risks=risks, output_dir=e2e_dir,
            base_url=resolved_base_url,
            project_name=active_profile.project.name if active_profile else project_root.name,
            llm_settings=llm_settings,
            cujs=cujs, auth_config=auth_config, browsers=browsers,
        )
        results["e2e"] = gen.generate()
        console.print("[green]  E2E Playwright project generated[/green]")
    else:
        console.print("[dim]  E2E: disabled[/dim]")

    # -- Data fixtures --
    if tests_settings and tests_settings.data and tests_settings.data.enabled:
        data_dir = Path(out) / "fixtures" if out else project_root / tests_settings.data.output_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        data_gen = DataGenerator(routes=routes)
        # Generate fixtures for each resource
        resources = set()
        for route in routes:
            parts = [p for p in route.path.split("/") if p and "{" not in p]
            if parts:
                resources.add(parts[0])
        for resource in resources:
            records = data_gen.generate(model_name=resource.capitalize(), count=tests_settings.data.count)
            out_file = data_dir / f"{resource}.{tests_settings.data.format}"
            data_gen.save(records, out_file, format=tests_settings.data.format)
        console.print(f"[green]  Data fixtures generated ({len(resources)} resources)[/green]")

    # -- Summary table --
    table = Table(title="Generation Summary")
    table.add_column("Suite", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("Tests", justify="right")
    table.add_column("LLM", style="magenta")
    table.add_column("Warnings", justify="right", style="yellow")

    for suite_name, result in results.items():
        table.add_row(
            suite_name,
            str(result.stats.get("files", 0)),
            str(result.stats.get("tests", 0)),
            "Yes" if result.llm_used else "No",
            str(len(result.warnings)),
        )

    console.print()
    console.print(table)


@generate_app.command("ci")
def generate_ci(
    platform: str = typer.Option("github", help="CI platform: github or gitlab"),
    project_name: Optional[str] = typer.Option(None, help="Project name for CI bootstrap"),
    framework: Optional[str] = typer.Option(None, help="Framework: fastapi, flask, django, nextjs"),
    python_version: str = typer.Option("3.11", help="Python version for CI"),
    out: Optional[str] = typer.Option(None, help="Output directory (defaults to project root)"),
    unit: bool = typer.Option(True, help="Include unit test stage"),
    behave: bool = typer.Option(False, help="Include BDD test stage"),
    e2e: bool = typer.Option(False, help="Include E2E test stage"),
    api_token: bool = typer.Option(False, help="Include API_TOKEN secret"),
):
    """Generate CI/CD pipeline template (GitHub Actions or GitLab CI)."""
    from qaagent.generators.cicd_generator import CICDGenerator, SuiteFlags

    # Resolve project name and framework from active profile if not specified
    resolved_name = project_name
    resolved_framework = framework

    try:
        active_entry, active_profile = load_active_profile()
    except Exception:
        active_profile = None

    if not resolved_name:
        if active_profile:
            resolved_name = active_profile.project.name
        else:
            resolved_name = Path.cwd().name

    if not resolved_framework:
        if active_profile:
            resolved_framework = active_profile.project.type or "fastapi"
        else:
            from qaagent.repo.validator import RepoValidator
            validator = RepoValidator(Path.cwd())
            resolved_framework = validator.detect_project_type() or "fastapi"

    # Resolve suite flags from config or CLI args
    suites = SuiteFlags(unit=unit, behave=behave, e2e=e2e)
    if active_profile and not any([behave, e2e]):
        # Auto-detect from profile
        if active_profile.tests.behave and active_profile.tests.behave.enabled:
            suites.behave = True
        if active_profile.tests.e2e and active_profile.tests.e2e.enabled:
            suites.e2e = True

    output_dir = Path(out) if out else Path.cwd()

    generator = CICDGenerator(
        framework=resolved_framework,
        project_name=resolved_name,
        python_version=python_version,
        suites=suites,
        api_token=api_token,
    )

    dest = generator.generate(platform, output_dir)
    console.print(f"[green]Generated {platform} CI pipeline → {dest}[/green]")
    console.print(f"  Framework: {resolved_framework}")
    console.print(f"  Project: {resolved_name}")
    console.print(f"  Suites: unit={suites.unit}, behave={suites.behave}, e2e={suites.e2e}")
    if platform == "github":
        console.print("  [yellow]Set BASE_URL in repository secrets[/yellow]")
    else:
        console.print("  [yellow]Set BASE_URL in CI/CD variables[/yellow]")


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
                ws = Workspace()
                output_file = ws.get_target_workspace(target_name) / output_file
            else:
                output_file = project_root / output_file
    else:
        if workspace:
            ws = Workspace()
            output_file = ws.get_openapi_path(target_name, format=format)
        else:
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

    console.print(f"[green]\u2713 OpenAPI spec generated \u2192 {output_file}[/green]")
    console.print(f"  Paths: {len(spec['paths'])}")
    console.print(f"  Schemas: {len(spec['components']['schemas'])}")

    if workspace:
        console.print(f"[yellow]  \u2192 Files in workspace (not in target project yet)[/yellow]")
        console.print(f"[yellow]  \u2192 Use 'qaagent workspace apply' to copy to target[/yellow]")
