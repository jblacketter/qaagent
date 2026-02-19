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


@branch_app.command("checklist")
def branch_checklist(
    branch_name: str = typer.Argument(..., help="Branch name to generate checklist for"),
    repo_path: str = typer.Option(".", help="Path to the git repository"),
    repo_id: Optional[str] = typer.Option(None, help="Repository ID"),
    base_branch: str = typer.Option("main", help="Base branch to diff against"),
):
    """Generate a test checklist from the branch diff."""
    from qaagent.branch.diff_analyzer import DiffAnalyzer
    from qaagent.branch.checklist_generator import generate_checklist
    from qaagent.branch import store

    path = Path(repo_path).resolve()
    if not (path / ".git").exists():
        console.print(f"[red]Not a git repository: {path}[/red]")
        raise typer.Exit(code=1)

    resolved_id = repo_id or path.name.lower().replace(" ", "-")

    # Find the branch card
    card = store.branch_get_by_name(resolved_id, branch_name)
    if card is None:
        console.print(f"[yellow]Branch '{branch_name}' not tracked. Run 'branch track' first.[/yellow]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Analyzing diff for {branch_name} vs {base_branch}...[/cyan]")

    analyzer = DiffAnalyzer(path, base_branch)
    diff = analyzer.analyze(branch_name)

    console.print(f"  Files changed: {len(diff.files)}")
    console.print(f"    Routes:     {len(diff.route_files)}")
    console.print(f"    Tests:      {len(diff.test_files)}")
    console.print(f"    Config:     {len(diff.config_files)}")
    console.print(f"    Migrations: {len(diff.migration_files)}")
    console.print(f"    Other:      {len(diff.other_files)}")
    console.print(f"  Lines: +{diff.total_additions} / -{diff.total_deletions}")

    checklist = generate_checklist(diff, branch_id=card.id)

    # Persist checklist
    checklist_id = store.checklist_create(checklist)

    console.print(f"\n[green]Generated checklist ({len(checklist.items)} items)[/green]")

    # Group by category for display
    by_category: dict[str, list] = {}
    for item in checklist.items:
        cat = item.category or "other"
        by_category.setdefault(cat, []).append(item)

    category_labels = {
        "route_change": "Route Changes",
        "data_integrity": "Data Integrity",
        "config": "Configuration",
        "regression": "Regression",
        "new_code": "New Code",
        "edge_case": "Edge Cases",
    }

    for cat, items in by_category.items():
        label = category_labels.get(cat, cat.replace("_", " ").title())
        console.print(f"\n  [bold]{label}[/bold]")
        for item in items:
            priority_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(item.priority, "white")
            console.print(f"    [ ] [{priority_color}]{item.description}[/{priority_color}]")


@branch_app.command("generate-tests")
def branch_generate_tests(
    branch_id: int = typer.Argument(..., help="Branch card ID"),
    repo_path: Optional[str] = typer.Option(None, help="Override repository path"),
    base_url: str = typer.Option("http://localhost:8000", help="Base URL for generated tests"),
):
    """Generate automated tests from routes changed in a branch."""
    from qaagent.branch import store
    from qaagent.branch.test_executor import generate_branch_tests
    from qaagent import db

    card = store.branch_get(branch_id)
    if card is None:
        console.print(f"[red]Branch card #{branch_id} not found.[/red]")
        raise typer.Exit(code=1)

    # Resolve repo path
    if repo_path:
        path = Path(repo_path).resolve()
    else:
        repo = db.repo_get(card.repo_id)
        if repo is None:
            console.print(f"[red]Repository '{card.repo_id}' not found in DB.[/red]")
            raise typer.Exit(code=1)
        path = Path(repo["path"])

    if not (path / ".git").exists():
        console.print(f"[red]Not a git repository: {path}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Generating tests for branch '{card.branch_name}'...[/cyan]")

    result = generate_branch_tests(
        repo_path=path,
        branch_name=card.branch_name,
        branch_id=card.id,
        base_branch=card.base_branch,
        base_url=base_url,
    )

    if result.warnings:
        for w in result.warnings:
            console.print(f"  [yellow]Warning: {w}[/yellow]")

    if result.files_generated:
        console.print(f"[green]Generated {result.test_count} tests in {result.files_generated} file(s)[/green]")
        console.print(f"  Output: {result.output_dir}")
    else:
        console.print("[yellow]No tests generated. Check warnings above.[/yellow]")


@branch_app.command("run-tests")
def branch_run_tests(
    branch_id: int = typer.Argument(..., help="Branch card ID"),
):
    """Run previously generated tests for a branch."""
    from qaagent.branch import store
    from qaagent.branch.test_executor import run_branch_tests
    from qaagent.branch.models import BranchTestRun

    card = store.branch_get(branch_id)
    if card is None:
        console.print(f"[red]Branch card #{branch_id} not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Running tests for branch '{card.branch_name}'...[/cyan]")

    try:
        result = run_branch_tests(card.id)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    # Store the result
    run = BranchTestRun(
        branch_id=card.id,
        run_id=result.run_id,
        suite_type=result.suite_type,
        total=result.total,
        passed=result.passed,
        failed=result.failed,
        skipped=result.skipped,
    )
    store.test_run_create(run)

    # Display results
    pass_pct = (result.passed / result.total * 100) if result.total > 0 else 0
    color = "green" if result.failed == 0 else "red"
    console.print(f"\n[{color}]Results: {result.passed}/{result.total} passed ({pass_pct:.0f}%)[/{color}]")
    if result.failed > 0:
        console.print(f"  [red]{result.failed} failed[/red]")
    if result.skipped > 0:
        console.print(f"  [yellow]{result.skipped} skipped[/yellow]")
    console.print(f"  Run ID: {result.run_id}")


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
