"""Config subcommands for the qaagent CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print

from ._helpers import (
    console,
    is_git_url,
    clone_repository,
    render_profile_template,
    resolve_project_path,
    target_manager,
)
from qaagent.config import (
    CONFIG_FILENAME,
    find_config_file,
    load_profile,
    load_config as load_legacy_config,
)

config_app = typer.Typer(help="Manage QA Agent configuration profiles")


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
    if path and is_git_url(path):
        project_path = clone_repository(path)
    else:
        project_path = resolve_project_path(path)
    config_path = project_path / CONFIG_FILENAME

    if config_path.exists() and not force:
        print(
            f"[yellow]Configuration already exists at {config_path}. Use --force to overwrite.[/yellow]"
        )
        raise typer.Exit(code=1)

    template_key = template.lower() if template else None
    try:
        content, resolved_template = render_profile_template(project_path, template_key)
    except ValueError as exc:  # unknown template
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    config_path.write_text(content, encoding="utf-8")
    print(f"[green]Created configuration:[/green] {config_path}")

    if register:
        manager = target_manager()
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
    project_path = resolve_project_path(path)
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
    project_path = resolve_project_path(path)
    config_file = find_config_file(project_path)
    if not config_file:
        print("[red]No .qaagent.yaml found. Run `qaagent config init` first.[/red]")
        raise typer.Exit(code=1)
    import yaml  # type: ignore

    profile = load_profile(config_file)
    print(f"[cyan]Configuration:[/cyan] {config_file}")
    console.print(yaml.safe_dump(profile.dict(), sort_keys=False))


@config_app.command("migrate")
def config_migrate(
    path: Optional[str] = typer.Option(None, help="Path to directory containing .qaagent.toml"),
    out: Optional[str] = typer.Option(None, help="Output path for .qaagent.yaml (defaults to same directory)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be generated without writing"),
):
    """Migrate legacy .qaagent.toml to .qaagent.yaml format."""
    import yaml  # type: ignore

    project_path = resolve_project_path(path)
    toml_path = project_path / ".qaagent.toml"

    if not toml_path.exists():
        print(f"[yellow]No .qaagent.toml found at {project_path}[/yellow]")
        print("[dim]Nothing to migrate.[/dim]")
        raise typer.Exit(code=0)

    # Load legacy config
    cfg = load_legacy_config(str(toml_path))
    if cfg is None:
        print(f"[red]Failed to parse {toml_path}[/red]")
        raise typer.Exit(code=1)

    # Build the new YAML profile structure
    profile_data = {
        "project": {
            "name": project_path.name,
            "type": "generic",
        },
        "openapi": {},
        "app": {},
    }

    if cfg.api.openapi:
        profile_data["openapi"]["spec_path"] = cfg.api.openapi
    if cfg.api.tags:
        profile_data["openapi"]["tags"] = cfg.api.tags
    if cfg.api.operations:
        profile_data["openapi"]["operations"] = cfg.api.operations
    if cfg.api.endpoint_pattern:
        profile_data["openapi"]["endpoint_pattern"] = cfg.api.endpoint_pattern

    if cfg.api.base_url:
        dev_env: dict = {"base_url": cfg.api.base_url}
        # Always carry auth settings so runtime commands get them
        auth = cfg.api.auth
        dev_env["auth"] = {
            "header_name": auth.header_name,
            "token_env": auth.token_env,
            "prefix": auth.prefix,
        }
        if cfg.api.timeout is not None:
            dev_env["timeout"] = cfg.api.timeout
        profile_data["app"]["dev"] = dev_env

    yaml_content = yaml.safe_dump(profile_data, sort_keys=False, default_flow_style=False)

    if dry_run:
        console.print(f"[cyan]Would generate .qaagent.yaml from {toml_path}:[/cyan]")
        console.print()
        console.print(yaml_content)
        console.print()
        console.print("[yellow]Run without --dry-run to write the file.[/yellow]")
        return

    # Determine output path
    if out:
        yaml_path = Path(out)
        if not yaml_path.is_absolute():
            yaml_path = project_path / yaml_path
    else:
        yaml_path = project_path / CONFIG_FILENAME

    if yaml_path.exists():
        print(f"[yellow]{yaml_path} already exists. Use a different --out path or remove the existing file.[/yellow]")
        raise typer.Exit(code=1)

    yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"[green]Migrated:[/green] {toml_path} -> {yaml_path}")
    console.print()
    console.print("[cyan]Generated .qaagent.yaml:[/cyan]")
    console.print(yaml_content)
    console.print("[yellow]Next steps:[/yellow]")
    console.print(f"  1. Review {yaml_path} and customize as needed")
    console.print(f"  2. Register as target: qaagent config init --force {project_path}")
    console.print(f"  3. Once verified, you can remove {toml_path}")
