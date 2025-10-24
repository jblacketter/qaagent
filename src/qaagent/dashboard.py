"""
Dashboard report generator for QA Agent.

Generates a visual HTML dashboard with charts, risk analysis, and test recommendations.
"""

from __future__ import annotations

import datetime
from collections import Counter
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from qaagent.analyzers.models import Risk, Route
from qaagent.analyzers.strategy_generator import build_strategy_summary


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def generate_dashboard(
    routes: List[Route],
    risks: List[Risk],
    output_path: Path | str,
    title: str = "QA Analysis Dashboard",
    project_name: str = "Project",
    enhanced: bool = True,
) -> Path:
    """
    Generate an interactive HTML dashboard report.

    Args:
        routes: List of discovered routes
        risks: List of assessed risks
        output_path: Where to save the dashboard HTML
        title: Dashboard title
        project_name: Name of the project
        enhanced: Use enhanced interactive dashboard (default: True)

    Returns:
        Path to generated dashboard
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build strategy summary
    strategy = build_strategy_summary(routes, risks)

    # Calculate risk summary
    risk_summary = {
        "critical": sum(1 for r in risks if r.severity.value == "critical"),
        "high": sum(1 for r in risks if r.severity.value == "high"),
        "medium": sum(1 for r in risks if r.severity.value == "medium"),
        "low": sum(1 for r in risks if r.severity.value == "low"),
    }

    # Calculate risk categories
    risk_categories = Counter(r.category.value for r in risks)

    # Get routes for display (all routes for enhanced, top 20 for basic)
    top_routes = routes if enhanced else routes[:20]

    # Convert routes to dictionaries for JSON serialization (needed for enhanced template)
    routes_dict = [
        {
            "method": r.method,
            "path": r.path,
            "auth_required": r.auth_required,
            "tags": r.tags,
            "source": r.source.value if hasattr(r.source, "value") else str(r.source),
        }
        for r in top_routes
    ]

    # Render template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template_name = "dashboard_enhanced.html.j2" if enhanced else "dashboard_report.html.j2"
    template = env.get_template(template_name)

    html_content = template.render(
        title=title,
        project_name=project_name,
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        strategy=strategy,
        risks=risks,
        risk_summary=risk_summary,
        risk_categories=dict(risk_categories),
        top_routes=top_routes,
        routes_dict=routes_dict,
    )

    output_path.write_text(html_content)

    return output_path


def generate_dashboard_from_workspace(
    target_name: str,
    output_path: Path | str | None = None,
) -> Path:
    """
    Generate dashboard from workspace data.

    Args:
        target_name: Name of the target
        output_path: Where to save dashboard (defaults to workspace)

    Returns:
        Path to generated dashboard
    """
    from qaagent.workspace import Workspace
    from qaagent.discovery import NextJsRouteDiscoverer
    from qaagent.analyzers.risk_assessment import assess_risks
    from qaagent.config.manager import TargetManager

    # Get target path
    manager = TargetManager()
    entry = manager.get(target_name)

    if not entry:
        raise ValueError(f"Target '{target_name}' not found")

    # Discover routes
    project_root = entry.resolved_path()
    discoverer = NextJsRouteDiscoverer(project_root)
    routes = discoverer.discover()

    # Assess risks
    risks = assess_risks(routes)

    # Determine output path
    if output_path is None:
        ws = Workspace()
        reports_dir = ws.get_reports_dir(target_name)
        output_path = reports_dir / "dashboard.html"

    # Generate dashboard
    return generate_dashboard(
        routes=routes,
        risks=risks,
        output_path=output_path,
        title=f"{target_name} QA Dashboard",
        project_name=target_name,
    )
