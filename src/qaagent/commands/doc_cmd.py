"""Doc subcommands for the qaagent CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print

from ._helpers import console

doc_app = typer.Typer(help="Application documentation generation and export")


@doc_app.command("generate")
def doc_generate(
    source: Optional[str] = typer.Option(None, help="Source directory to analyze"),
    openapi: Optional[str] = typer.Option(None, help="Path to OpenAPI spec file"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM prose synthesis"),
):
    """Generate or regenerate application documentation."""
    from qaagent.config import load_active_profile
    from qaagent.doc.generator import generate_documentation, save_documentation

    doc_settings = None
    openapi_path = None
    try:
        active_entry, active_profile = load_active_profile()
        project_root = active_entry.resolved_path()
        app_name = active_profile.project.name
        doc_settings = active_profile.doc
        if not openapi:
            openapi_path = active_profile.resolve_spec_path(project_root)
    except Exception:
        project_root = Path.cwd()
        app_name = project_root.name

    source_dir = Path(source) if source else project_root
    if openapi:
        openapi_path = Path(openapi)

    console.print(f"[cyan]Generating documentation for {app_name}...[/cyan]")

    doc = generate_documentation(
        source_dir=source_dir,
        openapi_path=openapi_path,
        app_name=app_name,
        use_llm=not no_llm,
        doc_settings=doc_settings,
    )

    output_path = save_documentation(doc, project_root)

    console.print(f"[green]✓[/green] Documentation generated: {output_path}")
    console.print(f"  Features: {len(doc.features)}")
    console.print(f"  Integrations: {len(doc.integrations)}")
    console.print(f"  Routes: {doc.total_routes}")
    console.print(f"  CUJs: {len(doc.discovered_cujs)}")


@doc_app.command("show")
def doc_show(
    section: Optional[str] = typer.Option(
        None, help="Section to display: features, integrations, cujs, summary"
    ),
):
    """Display documentation in the terminal."""
    from qaagent.config import load_active_profile
    from qaagent.doc.generator import load_documentation

    try:
        active_entry, _ = load_active_profile()
        project_root = active_entry.resolved_path()
    except Exception:
        project_root = Path.cwd()

    doc = load_documentation(project_root)
    if doc is None:
        console.print("[yellow]No documentation found. Run `qaagent doc generate` first.[/yellow]")
        raise typer.Exit(code=1)

    if section is None or section == "summary":
        console.print(f"\n[bold]{doc.app_name}[/bold]")
        console.print(f"Routes: {doc.total_routes} | Features: {len(doc.features)} | "
                       f"Integrations: {len(doc.integrations)} | CUJs: {len(doc.discovered_cujs)}")
        if doc.summary:
            console.print(f"\n{doc.summary}")

    if section is None or section == "features":
        if doc.features:
            console.print("\n[bold]Features[/bold]")
            for f in doc.features:
                crud = ", ".join(f.crud_operations).upper() if f.crud_operations else "—"
                auth = "🔒" if f.auth_required else "🔓"
                console.print(f"  {auth} {f.name} — {f.route_count} routes — CRUD: {crud}")

    if section is None or section == "integrations":
        if doc.integrations:
            console.print("\n[bold]Integrations[/bold]")
            for i in doc.integrations:
                vars_str = ", ".join(i.env_vars) if i.env_vars else "—"
                console.print(f"  [{i.type.value}] {i.name} — env: {vars_str}")

    if section is None or section == "cujs":
        if doc.discovered_cujs:
            console.print("\n[bold]Critical User Journeys[/bold]")
            for cuj in doc.discovered_cujs:
                console.print(f"  {cuj.name} ({len(cuj.steps)} steps)")

    console.print(f"\n[dim]Generated: {doc.generated_at} | Hash: {doc.content_hash}[/dim]")


@doc_app.command("export")
def doc_export(
    format: str = typer.Option("markdown", help="Export format: markdown or json"),
    output: Optional[str] = typer.Option(None, help="Output file path"),
):
    """Export documentation to a file."""
    from qaagent.config import load_active_profile
    from qaagent.doc.generator import load_documentation
    from qaagent.doc.markdown_export import render_markdown

    try:
        active_entry, _ = load_active_profile()
        project_root = active_entry.resolved_path()
    except Exception:
        project_root = Path.cwd()

    doc = load_documentation(project_root)
    if doc is None:
        console.print("[yellow]No documentation found. Run `qaagent doc generate` first.[/yellow]")
        raise typer.Exit(code=1)

    if format == "markdown":
        content = render_markdown(doc)
        default_name = "app-documentation.md"
    elif format == "json":
        content = doc.model_dump_json(indent=2)
        default_name = "app-documentation.json"
    else:
        console.print(f"[red]Unknown format: {format}. Use 'markdown' or 'json'.[/red]")
        raise typer.Exit(code=1)

    output_path = Path(output) if output else project_root / default_name
    output_path.write_text(content, encoding="utf-8")
    console.print(f"[green]✓[/green] Exported to {output_path}")


@doc_app.command("cujs")
def doc_cujs(
    format: str = typer.Option("table", help="Output format: table, json, or yaml"),
    merge: bool = typer.Option(False, "--merge", help="Merge discovered CUJs with existing cuj.yaml"),
):
    """Show auto-discovered critical user journeys."""
    import json

    from qaagent.config import load_active_profile
    from qaagent.doc.generator import load_documentation
    from qaagent.doc.cuj_discoverer import discover_cujs, to_cuj_config

    try:
        active_entry, _ = load_active_profile()
        project_root = active_entry.resolved_path()
    except Exception:
        project_root = Path.cwd()

    doc = load_documentation(project_root)
    if doc is None:
        console.print("[yellow]No documentation found. Run `qaagent doc generate` first.[/yellow]")
        raise typer.Exit(code=1)

    discovered = discover_cujs(doc.features)

    if not discovered:
        console.print("[yellow]No CUJs auto-discovered from routes.[/yellow]")
        raise typer.Exit(code=0)

    if format == "table":
        from rich.table import Table

        table = Table(title=f"Discovered CUJs ({len(discovered)})")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Pattern", style="green")
        table.add_column("Steps", style="yellow", justify="right")
        table.add_column("Confidence", style="magenta", justify="right")

        for cuj in discovered:
            table.add_row(
                cuj.id,
                cuj.name,
                cuj.pattern,
                str(len(cuj.steps)),
                f"{cuj.confidence:.0%}",
            )

        console.print(table)
    elif format == "json":
        data = [c.model_dump() for c in discovered]
        console.print(json.dumps(data, indent=2))
    elif format == "yaml":
        config = to_cuj_config(discovered)
        data = {
            "product": config.product,
            "journeys": [
                {
                    "id": j.id,
                    "name": j.name,
                    "components": j.components,
                    "apis": j.apis,
                    "acceptance": j.acceptance,
                }
                for j in config.journeys
            ],
        }
        try:
            import yaml
            console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))
        except ImportError:
            console.print(json.dumps(data, indent=2))
    else:
        console.print(f"[red]Unknown format: {format}. Use 'table', 'json', or 'yaml'.[/red]")
        raise typer.Exit(code=1)

    if merge:
        import yaml

        cuj_yaml_path = project_root / "handoff" / "cuj.yaml"
        config = to_cuj_config(discovered)
        existing_data: dict = {}
        existing_ids: set[str] = set()

        if cuj_yaml_path.exists():
            from qaagent.analyzers.cuj_config import CUJConfig as ExistingConfig
            existing = ExistingConfig.load(cuj_yaml_path)
            existing_ids = {j.id for j in existing.journeys}
            existing_data = yaml.safe_load(cuj_yaml_path.read_text(encoding="utf-8")) or {}

        new_journeys = [j for j in config.journeys if j.id not in existing_ids]
        if new_journeys:
            # Append new journeys to existing YAML data
            existing_journeys = existing_data.get("journeys", [])
            for j in new_journeys:
                existing_journeys.append({
                    "id": j.id,
                    "name": j.name,
                    "components": j.components,
                    "apis": j.apis,
                    "acceptance": j.acceptance,
                })
            existing_data.setdefault("product", config.product)
            existing_data["journeys"] = existing_journeys

            cuj_yaml_path.parent.mkdir(parents=True, exist_ok=True)
            cuj_yaml_path.write_text(
                yaml.dump(existing_data, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            console.print(f"\n[green]Added {len(new_journeys)} new CUJ(s) to {cuj_yaml_path}[/green]")
            for j in new_journeys:
                console.print(f"  + {j.name}")
        else:
            console.print("\n[dim]All discovered CUJs already exist in cuj.yaml[/dim]")
