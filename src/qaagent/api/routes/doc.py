"""API routes for application documentation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from qaagent.doc.generator import load_documentation, save_documentation, generate_documentation
from qaagent.doc.markdown_export import render_markdown
from qaagent.doc.models import (
    AppDocumentation,
    ArchitectureEdge,
    ArchitectureNode,
    DiscoveredCUJ,
    FeatureArea,
    Integration,
)

router = APIRouter(tags=["doc"])


def _get_doc() -> AppDocumentation:
    """Load documentation, raising 404 if not found."""
    try:
        from qaagent.config import load_active_profile
        entry, _ = load_active_profile()
        project_root = entry.resolved_path()
    except Exception:
        project_root = Path.cwd()

    doc = load_documentation(project_root)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="No documentation found. Run `qaagent doc generate` first.",
        )
    return doc


@router.get("/doc")
def get_doc() -> AppDocumentation:
    """Get the full application documentation."""
    return _get_doc()


@router.get("/doc/features")
def get_features() -> dict[str, list[FeatureArea]]:
    """Get all feature areas."""
    doc = _get_doc()
    return {"features": doc.features}


@router.get("/doc/features/{feature_id}")
def get_feature(feature_id: str) -> FeatureArea:
    """Get a specific feature area by ID."""
    doc = _get_doc()
    for feature in doc.features:
        if feature.id == feature_id:
            return feature
    raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")


@router.get("/doc/integrations")
def get_integrations() -> dict[str, list[Integration]]:
    """Get all detected integrations."""
    doc = _get_doc()
    return {"integrations": doc.integrations}


@router.get("/doc/cujs")
def get_cujs() -> dict[str, list[DiscoveredCUJ]]:
    """Get all discovered critical user journeys."""
    doc = _get_doc()
    return {"cujs": doc.discovered_cujs}


@router.get("/doc/architecture")
def get_architecture() -> dict:
    """Get architecture diagram data (nodes and edges)."""
    doc = _get_doc()
    return {
        "nodes": doc.architecture_nodes,
        "edges": doc.architecture_edges,
    }


class RegenerateRequest(BaseModel):
    no_llm: bool = False
    source_dir: Optional[str] = None


@router.post("/doc/regenerate")
def regenerate_doc(request: RegenerateRequest) -> AppDocumentation:
    """Regenerate application documentation."""
    try:
        from qaagent.config import load_active_profile
        entry, profile = load_active_profile()
        project_root = entry.resolved_path()
        app_name = profile.project.name
    except Exception:
        project_root = Path.cwd()
        app_name = project_root.name

    source_dir = Path(request.source_dir) if request.source_dir else project_root

    doc = generate_documentation(
        source_dir=source_dir,
        app_name=app_name,
        use_llm=not request.no_llm,
    )
    save_documentation(doc, project_root)
    return doc


@router.get("/doc/export/markdown")
def export_markdown() -> dict[str, str]:
    """Export documentation as markdown."""
    doc = _get_doc()
    return {"content": render_markdown(doc)}
