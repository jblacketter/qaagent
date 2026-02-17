"""API routes for application documentation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
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


def _resolve_project_root(repo_id: Optional[str]) -> Path:
    """Resolve project root from repo_id or fall back to active profile.

    - repo_id provided + found → repo path
    - repo_id provided + not found → 404
    - repo_id omitted → load_active_profile() fallback → cwd
    """
    if repo_id is not None:
        from qaagent.api.routes.repositories import repositories
        if repo_id not in repositories:
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{repo_id}' not found",
            )
        return Path(repositories[repo_id].path)

    # Fallback for CLI / no repo context
    try:
        from qaagent.config import load_active_profile
        entry, _ = load_active_profile()
        return entry.resolved_path()
    except Exception:
        return Path.cwd()


def _get_doc(repo_id: Optional[str] = None) -> AppDocumentation:
    """Load documentation, raising 404 if not found."""
    project_root = _resolve_project_root(repo_id)

    doc = load_documentation(project_root)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="No documentation found. Run `qaagent doc generate` first.",
        )
    return doc


@router.get("/doc")
def get_doc(repo_id: Optional[str] = Query(None)) -> AppDocumentation:
    """Get the full application documentation."""
    return _get_doc(repo_id)


@router.get("/doc/features")
def get_features(repo_id: Optional[str] = Query(None)) -> dict[str, list[FeatureArea]]:
    """Get all feature areas."""
    doc = _get_doc(repo_id)
    return {"features": doc.features}


@router.get("/doc/features/{feature_id}")
def get_feature(feature_id: str, repo_id: Optional[str] = Query(None)) -> FeatureArea:
    """Get a specific feature area by ID."""
    doc = _get_doc(repo_id)
    for feature in doc.features:
        if feature.id == feature_id:
            return feature
    raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")


@router.get("/doc/integrations")
def get_integrations(repo_id: Optional[str] = Query(None)) -> dict[str, list[Integration]]:
    """Get all detected integrations."""
    doc = _get_doc(repo_id)
    return {"integrations": doc.integrations}


@router.get("/doc/cujs")
def get_cujs(repo_id: Optional[str] = Query(None)) -> dict[str, list[DiscoveredCUJ]]:
    """Get all discovered critical user journeys."""
    doc = _get_doc(repo_id)
    return {"cujs": doc.discovered_cujs}


@router.get("/doc/architecture")
def get_architecture(repo_id: Optional[str] = Query(None)) -> dict:
    """Get architecture diagram data (nodes and edges)."""
    doc = _get_doc(repo_id)
    return {
        "nodes": doc.architecture_nodes,
        "edges": doc.architecture_edges,
    }


class RegenerateRequest(BaseModel):
    no_llm: bool = False
    source_dir: Optional[str] = None


@router.post("/doc/regenerate")
def regenerate_doc(request: RegenerateRequest, repo_id: Optional[str] = Query(None)) -> AppDocumentation:
    """Regenerate application documentation."""
    project_root = _resolve_project_root(repo_id)
    app_name = project_root.name

    doc_settings = None
    openapi_path = None

    # Try to load profile settings for richer config (only when no repo_id)
    if repo_id is None:
        try:
            from qaagent.config import load_active_profile
            entry, profile = load_active_profile()
            project_root = entry.resolved_path()
            app_name = profile.project.name
            doc_settings = profile.doc
            openapi_path = profile.resolve_spec_path(project_root)
        except Exception:
            pass
    else:
        from qaagent.api.routes.repositories import repositories
        app_name = repositories[repo_id].name

    source_dir = Path(request.source_dir) if request.source_dir else project_root

    doc = generate_documentation(
        source_dir=source_dir,
        openapi_path=openapi_path,
        app_name=app_name,
        use_llm=not request.no_llm,
        doc_settings=doc_settings,
    )
    save_documentation(doc, project_root)
    return doc


@router.get("/doc/export/markdown")
def export_markdown(repo_id: Optional[str] = Query(None)) -> dict[str, str]:
    """Export documentation as markdown."""
    doc = _get_doc(repo_id)
    return {"content": render_markdown(doc)}
