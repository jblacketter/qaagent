"""Branch Board CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from ._helpers import console

branch_app = typer.Typer(help="Branch Board — track branches and test readiness")


@branch_app.command("track")
def branch_track(
    repo_path: str = typer.Argument(..., help="Path to the git repository"),
    repo_id: Optional[str] = typer.Option(None, help="Repository ID (defaults to directory name)"),
    base_branch: str = typer.Option("main", help="Base branch to compare against"),
):
    """Scan a repository and track all branches."""
    from qaagent.branch.tracker import BranchTracker
    from qaagent import db

    path = Path(repo_path).resolve()
    if not (path / ".git").exists():
        console.print(f"[red]Not a git repository: {path}[/red]")
        raise typer.Exit(code=1)

    resolved_id = repo_id or path.name.lower().replace(" ", "-")

    # Ensure repo exists in DB
    existing = db.repo_get(resolved_id)
    if existing is None:
        db.repo_upsert(resolved_id, path.name, str(path), repo_type="local")

    console.print(f"[cyan]Scanning branches for {resolved_id} ({path})...[/cyan]")

    tracker = BranchTracker(path, resolved_id, base_branch)
    cards = tracker.scan()

    console.print(f"[green]Tracked {len(cards)} branch(es)[/green]")
    for card in cards:
        story = f" [{card.story_id}]" if card.story_id else ""
        console.print(
            f"  {card.stage.value:10s}  {card.branch_name}{story}"
            f"  ({card.commit_count} commits, {card.files_changed} files)"
        )


@branch_app.command("list")
def branch_list(
    repo_id: Optional[str] = typer.Option(None, help="Filter by repository ID"),
    stage: Optional[str] = typer.Option(None, help="Filter by stage"),
):
    """List tracked branches."""
    from qaagent.branch.models import BranchStage
    from qaagent.branch import store

    stage_filter = None
    if stage:
        try:
            stage_filter = BranchStage(stage)
        except ValueError:
            valid = ", ".join(s.value for s in BranchStage)
            console.print(f"[red]Invalid stage: {stage}. Valid: {valid}[/red]")
            raise typer.Exit(code=1)

    cards = store.branch_list(repo_id=repo_id, stage=stage_filter)
    if not cards:
        console.print("[yellow]No tracked branches found.[/yellow]")
        raise typer.Exit(code=0)

    table = Table(title=f"Branch Board ({len(cards)} branches)")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Branch", style="cyan")
    table.add_column("Stage", style="green")
    table.add_column("Story", style="yellow")
    table.add_column("Commits", justify="right")
    table.add_column("Files", justify="right")
    table.add_column("Summary", style="dim", max_width=50)

    for card in cards:
        table.add_row(
            str(card.id),
            card.branch_name,
            card.stage.value,
            card.story_id or "",
            str(card.commit_count),
            str(card.files_changed),
            (card.change_summary or "")[:50],
        )

    console.print(table)


@branch_app.command("show")
def branch_show(
    branch_id: int = typer.Argument(..., help="Branch card ID"),
):
    """Show details of a tracked branch."""
    from qaagent.branch import store

    card = store.branch_get(branch_id)
    if card is None:
        console.print(f"[red]Branch card #{branch_id} not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]{card.branch_name}[/bold]  (#{card.id})")
    console.print(f"  Repo:       {card.repo_id}")
    console.print(f"  Base:       {card.base_branch}")
    console.print(f"  Stage:      {card.stage.value}")
    console.print(f"  Story:      {card.story_id or '—'}")
    if card.story_url:
        console.print(f"  Story URL:  {card.story_url}")
    console.print(f"  Commits:    {card.commit_count}")
    console.print(f"  Files:      {card.files_changed}")
    if card.change_summary:
        console.print(f"  Summary:    {card.change_summary}")
    if card.notes:
        console.print(f"  Notes:      {card.notes}")
    console.print(f"  First seen: {card.first_seen_at or '—'}")
    console.print(f"  Updated:    {card.last_updated_at or '—'}")
    if card.merged_at:
        console.print(f"  Merged at:  {card.merged_at}")

    # Show checklist if exists
    checklist = store.checklist_get(card.id)
    if checklist:
        console.print(f"\n  [bold]Test Checklist[/bold] ({len(checklist.items)} items)")
        for item in checklist.items:
            status_icon = {"pending": " ", "passed": "x", "failed": "!", "skipped": "-"}.get(item.status, " ")
            priority_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(item.priority, "white")
            console.print(f"    [{status_icon}] [{priority_color}]{item.description}[/{priority_color}]")


@branch_app.command("update")
def branch_update_cmd(
    branch_id: int = typer.Argument(..., help="Branch card ID"),
    stage: Optional[str] = typer.Option(None, help="Set lifecycle stage"),
    story_id: Optional[str] = typer.Option(None, "--story", help="Set story/ticket ID"),
    story_url: Optional[str] = typer.Option(None, "--story-url", help="Set story/ticket URL"),
    notes: Optional[str] = typer.Option(None, help="Set notes"),
):
    """Update a branch card (stage, story, notes)."""
    from qaagent.branch.models import BranchCardUpdate, BranchStage
    from qaagent.branch import store

    stage_val = None
    if stage:
        try:
            stage_val = BranchStage(stage)
        except ValueError:
            valid = ", ".join(s.value for s in BranchStage)
            console.print(f"[red]Invalid stage: {stage}. Valid: {valid}[/red]")
            raise typer.Exit(code=1)

    update = BranchCardUpdate(
        stage=stage_val,
        story_id=story_id,
        story_url=story_url,
        notes=notes,
    )

    if not store.branch_update(branch_id, update):
        console.print(f"[red]Branch card #{branch_id} not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Updated branch card #{branch_id}[/green]")
