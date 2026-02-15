"""Render AppDocumentation as structured markdown."""

from __future__ import annotations

from .models import AppDocumentation, DiscoveredCUJ, FeatureArea, Integration


def render_markdown(doc: AppDocumentation) -> str:
    """Render AppDocumentation to a structured markdown string."""
    lines: list[str] = []

    # Title
    lines.append(f"# {doc.app_name} Documentation")
    lines.append("")

    # Summary
    if doc.summary:
        lines.append("## Summary")
        lines.append("")
        lines.append(doc.summary)
        lines.append("")

    # Features
    if doc.features:
        lines.append("## Features")
        lines.append("")
        for feature in doc.features:
            lines.extend(_render_feature(feature))
            lines.append("")

    # External Integrations
    if doc.integrations:
        lines.append("## External Integrations")
        lines.append("")
        for integration in doc.integrations:
            lines.extend(_render_integration(integration))
            lines.append("")

    # Critical User Journeys
    if doc.discovered_cujs:
        lines.append("## Critical User Journeys")
        lines.append("")
        for cuj in doc.discovered_cujs:
            lines.extend(_render_cuj(cuj))
            lines.append("")

    # Metadata footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated at {doc.generated_at} | {doc.total_routes} routes | Content hash: {doc.content_hash}*")
    lines.append("")

    return "\n".join(lines)


def _render_feature(feature: FeatureArea) -> list[str]:
    """Render a feature area section."""
    lines: list[str] = []

    # Header with badges
    badges = []
    if feature.crud_operations:
        crud_str = ", ".join(feature.crud_operations).upper()
        badges.append(f"CRUD: {crud_str}")
    if feature.auth_required:
        badges.append("Auth Required")

    header = f"### {feature.name}"
    if badges:
        header += f" ({' | '.join(badges)})"
    lines.append(header)
    lines.append("")

    if feature.description:
        lines.append(feature.description)
        lines.append("")

    # Routes table
    if feature.routes:
        lines.append("| Method | Path | Auth | Summary |")
        lines.append("|--------|------|------|---------|")
        for route in feature.routes:
            auth = "Yes" if route.auth_required else "No"
            summary = route.summary or "-"
            lines.append(f"| {route.method} | `{route.path}` | {auth} | {summary} |")
        lines.append("")

    return lines


def _render_integration(integration: Integration) -> list[str]:
    """Render an integration section."""
    lines: list[str] = []

    lines.append(f"### {integration.name}")
    lines.append("")
    lines.append(f"- **Type**: {integration.type.value}")

    if integration.package:
        lines.append(f"- **Package**: `{integration.package}`")

    if integration.env_vars:
        vars_str = ", ".join(f"`{v}`" for v in integration.env_vars)
        lines.append(f"- **Environment Variables**: {vars_str}")

    if integration.connected_features:
        features_str = ", ".join(integration.connected_features)
        lines.append(f"- **Connected Features**: {features_str}")

    if integration.description:
        lines.append("")
        lines.append(integration.description)

    lines.append("")
    return lines


def _render_cuj(cuj: DiscoveredCUJ) -> list[str]:
    """Render a discovered CUJ section."""
    lines: list[str] = []

    lines.append(f"### {cuj.name}")
    lines.append("")

    if cuj.description:
        lines.append(cuj.description)
        lines.append("")

    if cuj.steps:
        for step in cuj.steps:
            route_info = ""
            if step.route:
                route_info = f" (`{step.method or 'GET'} {step.route}`)"
            lines.append(f"{step.order}. {step.action}{route_info}")
        lines.append("")

    return lines
