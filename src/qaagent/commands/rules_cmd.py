"""CLI subcommands for managing risk rules."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table

from qaagent.analyzers.rules import BUILTIN_RULE_CLASSES, _builtin_ids, default_registry
from qaagent.analyzers.rules.yaml_loader import load_rules_from_dicts, load_rules_from_yaml, merge_custom_rules
from qaagent.config import load_active_profile
from qaagent.config.models import QAAgentProfile

rules_app = typer.Typer(help="Manage risk rules (built-in and custom)")
console = Console()


def _load_profile_and_root() -> Tuple[Optional[QAAgentProfile], Path]:
    """Load active profile and resolve project root.

    Returns (profile, project_root).  Falls back to (None, cwd) when
    no active target is configured.
    """
    try:
        entry, profile = load_active_profile()
        return profile, entry.resolved_path()
    except Exception:
        return None, Path.cwd()


def _build_registry_kwargs(
    profile: Optional[QAAgentProfile],
    project_root: Path,
) -> dict:
    """Build keyword args for default_registry() from profile."""
    kwargs: dict = {}
    if not profile:
        return kwargs
    ra = profile.risk_assessment
    if ra.custom_rules:
        kwargs["custom_rules"] = ra.custom_rules
    if ra.custom_rules_file:
        resolved = profile.resolve_custom_rules_path(project_root)
        if resolved:
            kwargs["custom_rules_file"] = resolved
    if ra.severity_overrides:
        kwargs["severity_overrides"] = ra.severity_overrides
    return kwargs


@rules_app.command("list")
def list_rules() -> None:
    """List all registered risk rules (built-in + custom)."""
    profile, project_root = _load_profile_and_root()
    kwargs = _build_registry_kwargs(profile, project_root)

    try:
        registry = default_registry(**kwargs)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]Error loading rules:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    builtin = _builtin_ids()

    table = Table(title="Risk Rules")
    table.add_column("ID", style="cyan")
    table.add_column("Category")
    table.add_column("Severity")
    table.add_column("Title")
    table.add_column("Source", style="dim")

    for rule in registry.rules:
        source = "built-in" if rule.rule_id in builtin else "custom"
        table.add_row(
            rule.rule_id,
            rule.category.value,
            rule.severity.value,
            rule.title,
            source,
        )

    console.print(table)
    console.print(f"\n{len(registry.rules)} rules total")


@rules_app.command("show")
def show_rule(rule_id: str = typer.Argument(help="Rule ID to display")) -> None:
    """Show details for a specific rule."""
    profile, project_root = _load_profile_and_root()
    kwargs = _build_registry_kwargs(profile, project_root)

    try:
        registry = default_registry(**kwargs)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]Error loading rules:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    rule = registry.get(rule_id)
    if not rule:
        console.print(f"[red]Rule '{rule_id}' not found.[/red]")
        raise typer.Exit(code=1)

    builtin = _builtin_ids()
    source = "built-in" if rule.rule_id in builtin else "custom"

    console.print(f"[bold]{rule.rule_id}[/bold] ({source})")
    console.print(f"  Category:    {rule.category.value}")
    console.print(f"  Severity:    {rule.severity.value}")
    console.print(f"  Title:       {rule.title}")
    console.print(f"  Description: {rule.description}")


@rules_app.command("validate")
def validate_rules(
    file: Optional[str] = typer.Argument(None, help="Path to custom rules YAML file"),
) -> None:
    """Validate a custom rules YAML file or the active profile's custom rules."""
    builtin = _builtin_ids()

    if file:
        path = Path(file)
        if not path.exists():
            console.print(f"[red]File not found:[/red] {path}")
            raise typer.Exit(code=1)
        try:
            rules = load_rules_from_yaml(path, builtin_ids=builtin)
            console.print(f"[green]Valid:[/green] {len(rules)} rule(s) in {path.name}")
            for r in rules:
                console.print(f"  {r.rule_id}: {r.title}")
        except (ValueError, FileNotFoundError) as exc:
            console.print(f"[red]Validation error:[/red] {exc}")
            raise typer.Exit(code=1) from exc
        return

    # Validate custom rules from active profile (file + inline + cross-source)
    profile, project_root = _load_profile_and_root()
    if not profile:
        console.print("No custom rules found in active profile.")
        return

    ra = profile.risk_assessment
    has_inline = bool(ra.custom_rules)
    rules_file_path = profile.resolve_custom_rules_path(project_root) if ra.custom_rules_file else None
    has_file = rules_file_path is not None

    if not has_inline and not has_file:
        console.print("No custom rules found in active profile.")
        return

    try:
        rules = merge_custom_rules(
            file_path=rules_file_path,
            inline_rules=ra.custom_rules if has_inline else None,
            builtin_ids=builtin,
        )
        # Report sources validated
        sources = []
        if has_file:
            sources.append(f"file ({rules_file_path.name})")
        if has_inline:
            sources.append("inline")
        console.print(f"[green]Valid:[/green] {len(rules)} rule(s) from {' + '.join(sources)}")
        for r in rules:
            console.print(f"  {r.rule_id}: {r.title}")
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
