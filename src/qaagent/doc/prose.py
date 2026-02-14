"""LLM prose synthesis with template fallback for app documentation."""

from __future__ import annotations

from typing import List

from .models import AppDocumentation, FeatureArea, Integration


def _template_app_summary(doc: AppDocumentation) -> str:
    """Generate a template-based app summary."""
    parts = [f"{doc.app_name} is an application"]

    if doc.features:
        feature_names = [f.name for f in doc.features[:5]]
        parts.append(f" with {len(doc.features)} feature area(s)")
        parts.append(f" including {', '.join(feature_names)}")
        if len(doc.features) > 5:
            parts.append(f" and {len(doc.features) - 5} more")

    parts.append(f". It exposes {doc.total_routes} API route(s)")

    if doc.integrations:
        int_names = [i.name for i in doc.integrations[:3]]
        parts.append(f" and integrates with {', '.join(int_names)}")
        if len(doc.integrations) > 3:
            parts.append(f" and {len(doc.integrations) - 3} other service(s)")

    parts.append(".")
    return "".join(parts)


def _template_feature_description(feature: FeatureArea) -> str:
    """Generate a template-based feature description."""
    parts = [f"{feature.name} provides"]

    if feature.crud_operations:
        parts.append(f" {', '.join(feature.crud_operations)} operations")
    else:
        parts.append(f" {len(feature.routes)} endpoint(s)")

    if feature.auth_required:
        parts.append(" (authentication required)")

    parts.append(f" across {len(feature.routes)} route(s).")

    if feature.tags:
        parts.append(f" Tags: {', '.join(feature.tags)}.")

    return "".join(parts)


def _template_integration_description(integration: Integration) -> str:
    """Generate a template-based integration description."""
    parts = [f"{integration.name} ({integration.type.value})"]

    if integration.package:
        parts.append(f" via the {integration.package} package")

    if integration.env_vars:
        parts.append(f". Configured with environment variable(s): {', '.join(integration.env_vars)}")

    parts.append(".")
    return "".join(parts)


def synthesize_prose(
    doc: AppDocumentation,
    *,
    use_llm: bool = True,
) -> AppDocumentation:
    """Add prose descriptions to an AppDocumentation object.

    Uses LLM when available and use_llm=True; falls back to templates otherwise.
    """
    llm_available = False
    client = None

    if use_llm:
        try:
            from ..llm import LLMClient, ChatMessage
            client = LLMClient()
            llm_available = client.available()
        except Exception:
            llm_available = False

    if llm_available and client is not None:
        doc = _llm_synthesis(doc, client)
    else:
        doc = _template_synthesis(doc)

    return doc


def _template_synthesis(doc: AppDocumentation) -> AppDocumentation:
    """Apply template-based descriptions."""
    doc.summary = _template_app_summary(doc)

    for feature in doc.features:
        if not feature.description:
            feature.description = _template_feature_description(feature)

    for integration in doc.integrations:
        if not integration.description:
            integration.description = _template_integration_description(integration)

    return doc


def _llm_synthesis(doc: AppDocumentation, client: object) -> AppDocumentation:
    """Use LLM to generate richer prose descriptions."""
    from ..llm import LLMClient, ChatMessage

    assert isinstance(client, LLMClient)

    # Generate app summary
    try:
        feature_list = "\n".join(
            f"- {f.name}: {f.route_count} routes, CRUD: {', '.join(f.crud_operations) or 'none'}"
            for f in doc.features
        )
        integration_list = "\n".join(
            f"- {i.name} ({i.type.value})"
            for i in doc.integrations
        )
        prompt = (
            f"Write a concise 2-3 sentence summary of this application.\n\n"
            f"App: {doc.app_name}\n"
            f"Total routes: {doc.total_routes}\n"
            f"Features:\n{feature_list}\n"
            f"Integrations:\n{integration_list or 'none detected'}\n"
        )
        response = client.chat([
            ChatMessage(role="system", content="You are a technical writer. Write concise, factual application summaries."),
            ChatMessage(role="user", content=prompt),
        ])
        doc.summary = response.content.strip()
    except Exception:
        doc.summary = _template_app_summary(doc)

    # Generate feature descriptions
    for feature in doc.features:
        if not feature.description:
            try:
                routes_info = "\n".join(
                    f"  {r.method} {r.path} — {r.summary or 'no summary'}"
                    for r in feature.routes
                )
                prompt = (
                    f"Write a 1-2 sentence description of this feature area.\n\n"
                    f"Feature: {feature.name}\n"
                    f"Routes:\n{routes_info}\n"
                    f"CRUD: {', '.join(feature.crud_operations) or 'none'}\n"
                    f"Auth required: {feature.auth_required}\n"
                )
                response = client.chat([
                    ChatMessage(role="system", content="You are a technical writer. Write concise feature descriptions."),
                    ChatMessage(role="user", content=prompt),
                ])
                feature.description = response.content.strip()
            except Exception:
                feature.description = _template_feature_description(feature)

    # Generate integration descriptions
    for integration in doc.integrations:
        if not integration.description:
            integration.description = _template_integration_description(integration)

    return doc
