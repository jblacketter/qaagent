"""Workspace subcommands for the qaagent CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print

from ._helpers import console
from qaagent.config import load_active_profile

workspace_app = typer.Typer(help="Manage workspace for generated artifacts")


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
                console.print(f"  [OK] {filename} ({size_kb:.1f} KB)")
            elif filename == "tests":
                unit_count = file_info.get("unit", 0)
                behave_count = file_info.get("behave", 0)
                if unit_count > 0:
                    console.print(f"  [OK] tests/unit/ ({unit_count} files)")
                if behave_count > 0:
                    console.print(f"  [OK] tests/behave/ ({behave_count} files)")
            elif filename == "reports":
                console.print(f"  [OK] reports/ ({file_info} files)")
            elif filename == "fixtures":
                console.print(f"  [OK] fixtures/ ({file_info} files)")
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
        console.print(f"  - {target_name} ({file_count} files)")


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
        console.print("[green][OK] All workspaces cleaned[/green]")
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
    console.print(f"[green][OK] Workspace cleaned for '{target}'[/green]")


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
        console.print(f"[green][OK] Copied {len(copied)} files to target:[/green]")

    for src, dest in copied:
        rel_dest = dest.relative_to(target_path) if dest.is_relative_to(target_path) else dest
        console.print(f"  {src.name} -> {rel_dest}")
