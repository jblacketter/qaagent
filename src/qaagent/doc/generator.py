"""Documentation generator orchestrator.

Calls discover_routes() → FeatureGrouper → IntegrationDetector → prose synthesis
→ returns AppDocumentation. Includes save/load for appdoc.json.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..analyzers.models import Route
from ..analyzers.route_discovery import discover_routes
from .feature_grouper import group_routes
from .integration_detector import IntegrationDetector
from .models import AppDocumentation, FeatureArea, Integration
from .prose import synthesize_prose
from .cuj_discoverer import discover_cujs
from .graph_builder import build_all_graphs
from .role_discoverer import discover_roles
from .journey_builder import build_user_journeys

# Default storage location within .qaagent/ directory
APPDOC_FILENAME = "appdoc.json"


def _compute_content_hash(routes: List[Route], integrations: List[Integration]) -> str:
    """Compute a content hash for staleness detection."""
    data = {
        "routes": sorted((r.method, r.path) for r in routes),
        "integrations": sorted(i.id for i in integrations),
    }
    raw = json.dumps(data, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _link_integrations_to_features(
    features: List[FeatureArea],
    integrations: List[Integration],
) -> None:
    """Link integrations to features based on overlapping route prefixes and tags.

    This is a heuristic: if an integration's connected_features list is empty,
    we connect it to all features (since we can't determine scope from imports alone).
    If connected_features is set (e.g. from config overrides), we honor that.
    """
    feature_ids = {f.id for f in features}
    all_feature_ids = sorted(feature_ids)
    for integration in integrations:
        if integration.connected_features:
            # Validate and keep only existing feature IDs
            integration.connected_features = [
                fid for fid in integration.connected_features if fid in feature_ids
            ]
        else:
            # Connect to all features when scope can't be determined from imports
            integration.connected_features = list(all_feature_ids)


def _detect_tech_stack(source_dir: Path) -> List[str]:
    """Detect technologies and frameworks from manifest files."""
    tech: List[str] = []

    # Python
    if (source_dir / "pyproject.toml").exists() or (source_dir / "requirements.txt").exists():
        tech.append("Python")
        try:
            toml_text = (source_dir / "pyproject.toml").read_text(encoding="utf-8")
            if "fastapi" in toml_text.lower():
                tech.append("FastAPI")
            if "django" in toml_text.lower():
                tech.append("Django")
            if "flask" in toml_text.lower():
                tech.append("Flask")
        except (OSError, UnicodeDecodeError):
            pass
        try:
            req_text = (source_dir / "requirements.txt").read_text(encoding="utf-8").lower()
            if "fastapi" in req_text and "FastAPI" not in tech:
                tech.append("FastAPI")
            if "django" in req_text and "Django" not in tech:
                tech.append("Django")
            if "flask" in req_text and "Flask" not in tech:
                tech.append("Flask")
        except (OSError, UnicodeDecodeError):
            pass

    # Node.js / JavaScript / TypeScript
    pkg_json = source_dir / "package.json"
    if pkg_json.exists():
        try:
            pkg_text = pkg_json.read_text(encoding="utf-8").lower()
            if "typescript" in pkg_text:
                tech.append("TypeScript")
            else:
                tech.append("JavaScript")
            if "next" in pkg_text:
                tech.append("Next.js")
            if "react" in pkg_text:
                tech.append("React")
            if "vue" in pkg_text:
                tech.append("Vue.js")
            if "angular" in pkg_text:
                tech.append("Angular")
            if "express" in pkg_text:
                tech.append("Express")
        except (OSError, UnicodeDecodeError):
            tech.append("JavaScript")

    # Go
    if (source_dir / "go.mod").exists():
        tech.append("Go")

    # Rust
    if (source_dir / "Cargo.toml").exists():
        tech.append("Rust")

    # Java / Kotlin
    if (source_dir / "pom.xml").exists() or (source_dir / "build.gradle").exists():
        tech.append("Java")

    # Ruby
    if (source_dir / "Gemfile").exists():
        tech.append("Ruby")

    return tech


def _apply_doc_settings(
    doc_settings: object,
    integrations: List[Integration],
    features: List[FeatureArea],
) -> tuple[List[Integration], List[FeatureArea]]:
    """Apply DocSettings overrides: merge config integrations, exclude features."""
    from ..config.models import DocSettings

    if not isinstance(doc_settings, DocSettings):
        return integrations, features

    # Merge manual integration overrides
    existing_ids = {i.id for i in integrations}
    for override in doc_settings.integrations:
        from .integration_detector import _slugify, _canonical_id, IntegrationType
        iid = _canonical_id(_slugify(override.name))
        if iid in existing_ids:
            # Merge: update existing
            for existing in integrations:
                if existing.id == iid:
                    if override.description:
                        existing.description = override.description
                    if override.type and override.type != "unknown":
                        try:
                            existing.type = IntegrationType(override.type)
                        except ValueError:
                            pass
                    if override.env_vars:
                        for v in override.env_vars:
                            if v not in existing.env_vars:
                                existing.env_vars.append(v)
                    if override.connected_features:
                        existing.connected_features = override.connected_features
                    existing.source = "config"
                    break
        else:
            # Add new integration from config
            try:
                itype = IntegrationType(override.type)
            except ValueError:
                itype = IntegrationType.UNKNOWN
            integrations.append(Integration(
                id=iid,
                name=override.name,
                type=itype,
                description=override.description,
                env_vars=override.env_vars,
                connected_features=override.connected_features,
                source="config",
            ))
            existing_ids.add(iid)

    # Exclude features by pattern
    import fnmatch
    if doc_settings.exclude_features:
        features = [
            f for f in features
            if not any(fnmatch.fnmatch(f.id, pat) for pat in doc_settings.exclude_features)
        ]

    return integrations, features


def generate_documentation(
    *,
    source_dir: Optional[Path] = None,
    openapi_path: Optional[Path] = None,
    app_name: Optional[str] = None,
    use_llm: bool = True,
    routes: Optional[List[Route]] = None,
    doc_settings: Optional[object] = None,
) -> AppDocumentation:
    """Generate complete app documentation from code analysis.

    Args:
        source_dir: Directory containing application source code.
        openapi_path: Path to OpenAPI spec file.
        app_name: Application name (auto-detected from config if not provided).
        use_llm: Whether to use LLM for prose synthesis.
        routes: Pre-discovered routes (skips route discovery if provided).

    Returns:
        AppDocumentation with features, integrations, and prose.
    """
    # Step 1: Discover routes
    if routes is None:
        # Only pass openapi_path if the file actually exists
        effective_openapi = None
        if openapi_path and Path(openapi_path).exists():
            effective_openapi = str(openapi_path)
        routes = discover_routes(
            openapi_path=effective_openapi,
            source_path=str(source_dir) if source_dir else None,
        )

    # Step 2: Group routes into feature areas
    features = group_routes(routes)

    # Step 3: Detect integrations
    integrations: List[Integration] = []
    if source_dir and source_dir.exists():
        detector = IntegrationDetector()
        integrations = detector.detect(source_dir)

    # Step 4: Apply config overrides
    if doc_settings is not None:
        integrations, features = _apply_doc_settings(doc_settings, integrations, features)

    # Step 5: Link integrations to features
    _link_integrations_to_features(features, integrations)

    # Step 6: Compute content hash
    content_hash = _compute_content_hash(routes, integrations)

    # Step 7: Detect tech stack
    tech_stack: List[str] = []
    if source_dir and source_dir.exists():
        tech_stack = _detect_tech_stack(source_dir)

    # Build documentation object
    doc = AppDocumentation(
        app_name=app_name or "Application",
        generated_at=datetime.now().isoformat(),
        content_hash=content_hash,
        source_dir=str(source_dir) if source_dir else None,
        features=features,
        integrations=integrations,
        total_routes=len(routes),
        tech_stack=tech_stack,
    )

    # Discover CUJs
    doc.discovered_cujs = discover_cujs(features)

    # Discover user roles
    doc.user_roles = discover_roles(features)

    # Build user journeys from CUJs
    doc.user_journeys = build_user_journeys(doc.discovered_cujs, features)

    # Build architecture graphs
    doc = build_all_graphs(doc)

    # Prose synthesis
    doc = synthesize_prose(doc, use_llm=use_llm)

    # Apply custom summary override (after prose synthesis so it takes precedence)
    if doc_settings is not None:
        from ..config.models import DocSettings
        if isinstance(doc_settings, DocSettings) and doc_settings.custom_summary:
            doc.summary = doc_settings.custom_summary

    return doc


def save_documentation(doc: AppDocumentation, project_root: Path) -> Path:
    """Save documentation to .qaagent/appdoc.json."""
    qaagent_dir = project_root / ".qaagent"
    qaagent_dir.mkdir(parents=True, exist_ok=True)
    output_path = qaagent_dir / APPDOC_FILENAME
    output_path.write_text(
        doc.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return output_path


def load_documentation(project_root: Path) -> Optional[AppDocumentation]:
    """Load documentation from .qaagent/appdoc.json."""
    doc_path = project_root / ".qaagent" / APPDOC_FILENAME
    if not doc_path.exists():
        return None
    try:
        data = json.loads(doc_path.read_text(encoding="utf-8"))
        return AppDocumentation.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None
