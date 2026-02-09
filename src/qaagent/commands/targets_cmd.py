"""Targets subcommands and `use` top-level command for the qaagent CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.table import Table

from ._helpers import console, target_manager
from qaagent.config import load_active_profile
from qaagent.config.detect import detect_project_type

targets_app = typer.Typer(help="Manage registered QA Agent targets")


@targets_app.command("list")
def targets_list() -> None:
    manager = target_manager()
    registry = manager.registry
    entries = list(manager.list_targets())
    table = Table(title="Registered Targets", show_lines=False)
    table.add_column("Active", style="green", no_wrap=True)
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Type", style="magenta")

    for entry in entries:
        is_active = "\u2605" if registry.active == entry.name else ""
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
    manager = target_manager()
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
    manager = target_manager()
    try:
        manager.remove_target(name)
        print(f"[green]Removed target `{name}`[/green]")
    except ValueError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


def use_target(name: str = typer.Argument(..., help="Target name to activate")) -> None:
    """Activate a registered target."""
    manager = target_manager()
    try:
        entry = manager.set_active(name)
    except ValueError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    else:
        print(f"[green]Active target:[/green] {entry.name} \u2192 {entry.path}")
