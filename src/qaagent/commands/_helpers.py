"""Shared CLI helpers and utilities for qaagent command modules."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import typer
from pydantic import BaseModel
from rich import print
from rich.console import Console
from rich.table import Table

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route
from qaagent.config import (
    TargetManager,
    TemplateContext,
    available_templates,
    render_template,
)
from qaagent.config.detect import (
    default_base_url,
    default_source_dir,
    default_spec_path,
    default_start_command,
    detect_project_type,
)

console = Console()


class AnalyzeSummary(BaseModel):
    root: str
    language_hints: list[str]
    frameworks: list[str]
    detected: list[str]
    recommendations: list[str]


def load_json_or_yaml(path: Path) -> Dict:
    """Load a JSON or YAML file and return its contents as a dict."""
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


def load_routes_from_file(path: Path) -> List[Route]:
    """Load routes from a JSON or YAML file."""
    payload = load_json_or_yaml(path)
    data: Iterable = payload.get("routes", payload) if isinstance(payload, dict) else payload
    return [Route.from_dict(item) for item in data]


def load_risks_from_file(path: Path) -> List[Risk]:
    """Load risks from a JSON or YAML file."""
    payload = load_json_or_yaml(path)
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


def print_routes_table(routes: List[Route], verbose: bool = False) -> None:
    """Print a rich table of discovered routes."""
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


def target_manager() -> TargetManager:
    """Get a TargetManager instance."""
    return TargetManager()


def resolve_project_path(path: Optional[str]) -> Path:
    """Resolve a project path from an optional string argument."""
    if path:
        return Path(path).expanduser().resolve()
    return Path.cwd().resolve()


def render_profile_template(project_path: Path, template_name: Optional[str]) -> tuple[str, str]:
    """Render a profile template for a project, returning (content, project_type)."""
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


def detect_stack(root: Path) -> AnalyzeSummary:
    """Heuristic detection of project stack and QA recommendations."""
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


def is_git_url(path_or_url: str) -> bool:
    """Check if a string is a Git repository URL."""
    if not path_or_url:
        return False
    return (
        path_or_url.startswith("https://")
        or path_or_url.startswith("http://")
        or path_or_url.startswith("git@")
    )


def clone_repository(url: str) -> Path:
    """Clone a repository and return its local path."""
    try:
        from qaagent.repo.cloner import RepoCloner
        from qaagent.repo.cache import RepoCache

        print(f"[cyan]Cloning repository from {url}...[/cyan]")

        cloner = RepoCloner()
        cache = RepoCache()

        local_path = cloner.clone(url, depth=1)
        cache.register_clone(url, local_path)

        print(f"[green][OK][/green] Cloned to {local_path}")
        return local_path

    except Exception as e:
        print(f"[red]Failed to clone repository: {e}[/red]")
        raise typer.Exit(code=1)


def module_available(name: str) -> bool:
    """Check if a Python module is importable."""
    return importlib.util.find_spec(name) is not None


def print_fix_result(result) -> None:
    """Print the result of an auto-fix operation."""
    if result.success:
        if result.files_modified > 0:
            console.print(f"[green]  [OK] {result.message}[/green]")
        else:
            console.print(f"[dim]  [OK] {result.message} (no changes needed)[/dim]")
    else:
        console.print(f"[red]  [FAIL] {result.message}[/red]")
        for error in result.errors:
            console.print(f"[red]    {error}[/red]")
