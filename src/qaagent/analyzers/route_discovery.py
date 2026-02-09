from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ..openapi_utils import enumerate_operations, load_openapi
from .models import Route, RouteSource

try:
    from ..discovery.nextjs_parser import NextJsRouteDiscoverer

    NEXTJS_AVAILABLE = True
except ImportError:
    NEXTJS_AVAILABLE = False

try:
    from ..discovery import get_framework_parser

    FRAMEWORK_PARSERS_AVAILABLE = True
except ImportError:
    FRAMEWORK_PARSERS_AVAILABLE = False


def _load_spec(path: str | Path) -> Dict:
    return load_openapi(str(path))


def _operation_auth_required(operation: Dict, global_security: Iterable, security_schemes: Dict) -> bool:
    if operation is None:
        return False

    # Operation-level security overrides global
    op_security = operation.get("security")
    if op_security is None:
        op_security = global_security

    if not op_security:
        return False

    # Example: [{"api_key": []}, {"oauth": ["read"]}]
    for requirement in op_security:
        if not requirement:  # An empty dict means optional security
            continue
        for scheme_name in requirement:
            scheme = security_schemes.get(scheme_name)
            if scheme:
                return True
    return False


def _parameters_for_operation(path_item: Dict, operation: Dict) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    params = []

    # Path-level params apply to all operations
    if isinstance(path_item, dict):
        params.extend(path_item.get("parameters", []) or [])
    # Operation-level params override
    if isinstance(operation, dict):
        params.extend(operation.get("parameters", []) or [])

    for param in params:
        location = param.get("in", "query")
        grouped[location].append(param)

    # Request body
    if isinstance(operation, dict) and operation.get("requestBody"):
        grouped["body"].append(operation["requestBody"])

    return {key: value for key, value in grouped.items()}


def discover_from_openapi(spec_path: str | Path) -> List[Route]:
    """Discover routes from an OpenAPI/Swagger specification."""
    spec = _load_spec(spec_path)
    components = spec.get("components", {}) or {}
    security_schemes = components.get("securitySchemes", {}) or {}
    global_security = spec.get("security", []) or []

    path_items = spec.get("paths", {}) or {}

    routes: List[Route] = []
    for op in enumerate_operations(spec):
        path_item = path_items.get(op.path, {})
        operation = path_item.get(op.method.lower(), {})

        auth_required = _operation_auth_required(operation, global_security, security_schemes)
        params = _parameters_for_operation(path_item, operation)
        responses = (operation or {}).get("responses", {}) or {}

        metadata = {
            "operation_id": op.operation_id,
            "tags": op.tags,
            "security": operation.get("security", global_security),
            "summary": operation.get("summary"),
            "deprecated": operation.get("deprecated", False),
        }
        routes.append(
            Route(
                path=op.path,
                method=op.method,
                auth_required=auth_required,
                summary=operation.get("summary"),
                description=operation.get("description"),
                tags=op.tags,
                params=params,
                responses=responses,
                source=RouteSource.OPENAPI,
                confidence=1.0,
                metadata=metadata,
            )
        )
    return routes


def deduplicate_routes(routes: List[Route]) -> List[Route]:
    """Merge duplicate routes keeping the highest-confidence metadata."""
    merged: Dict[tuple[str, str], Route] = {}
    for route in routes:
        key = (route.method.upper(), route.path)
        if key not in merged:
            merged[key] = route
            continue

        existing = merged[key]
        if route.confidence > existing.confidence:
            merged[key] = route
            continue

        # Merge metadata such as tags
        existing.tags = sorted(set(existing.tags) | set(route.tags))
        existing.metadata.update(route.metadata)
        for category, items in route.params.items():
            existing.params.setdefault(category, [])
            existing.params[category].extend(
                item for item in items if item not in existing.params[category]
            )
    return list(merged.values())


def _is_nextjs_project(path: Path) -> bool:
    """Check if a directory is a Next.js project."""
    # Check for Next.js indicators
    if (path / "next.config.js").exists() or (path / "next.config.mjs").exists():
        return True
    if (path / "next.config.ts").exists():
        return True
    if (path / "package.json").exists():
        try:
            import json as json_lib

            pkg = json_lib.loads((path / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                return True
        except Exception:
            pass
    return False


def discover_from_nextjs(project_root: str | Path) -> List[Route]:
    """Discover routes from Next.js App Router source code."""
    if not NEXTJS_AVAILABLE:
        return []

    try:
        discoverer = NextJsRouteDiscoverer(Path(project_root))
        routes = discoverer.discover()
        # Convert to proper Route objects with SOURCE
        for route in routes:
            route.source = RouteSource.CODE
            route.confidence = 0.9  # High confidence from source code
        return routes
    except Exception as e:
        # Return empty list on error but don't crash
        return []


def discover_from_source(source_dir: str | Path, framework: Optional[str] = None) -> List[Route]:
    """Discover routes from Python framework source code.

    Args:
        source_dir: Path to source code directory
        framework: Framework name ("fastapi", "flask", "django"). Auto-detected if not provided.

    Returns:
        List of discovered Route objects
    """
    if not FRAMEWORK_PARSERS_AVAILABLE:
        return []

    source_path = Path(source_dir)
    if not source_path.exists():
        return []

    # Auto-detect framework if not specified
    if not framework:
        from ..repo.validator import RepoValidator

        validator = RepoValidator(source_path)
        framework = validator.detect_project_type()

    if not framework or framework in ("nextjs", "express"):
        return []

    parser = get_framework_parser(framework)
    if parser is None:
        return []

    try:
        return parser.parse(source_path)
    except Exception:
        return []


def discover_routes(
    target: Optional[str] = None,
    openapi_path: Optional[str | Path] = None,
    source_path: Optional[str | Path] = None,
    auto_discover_nextjs: bool = False,
) -> List[Route]:
    """Aggregate routes discovered from multiple sources.

    Args:
        target: Target name from config (uses active target if not provided)
        openapi_path: Path to OpenAPI spec file
        source_path: Path to source code directory
        auto_discover_nextjs: Auto-discover Next.js App Router routes

    Returns:
        List of discovered Route objects
    """
    routes: List[Route] = []

    if openapi_path:
        routes.extend(discover_from_openapi(openapi_path))

    # Auto-discover Next.js routes
    if auto_discover_nextjs or (source_path and _is_nextjs_project(Path(source_path))):
        project_root = source_path or Path(".")
        nextjs_routes = discover_from_nextjs(project_root)
        if nextjs_routes:
            routes.extend(nextjs_routes)

    # Auto-discover Python framework routes
    if source_path and not _is_nextjs_project(Path(source_path)):
        source_routes = discover_from_source(source_path)
        if source_routes:
            routes.extend(source_routes)

    if target:
        # Placeholder for runtime crawling
        pass

    return deduplicate_routes(routes)


def export_routes(routes: List[Route], dest: Path, format: str = "json") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if format == "yaml":
        try:
            import yaml  # type: ignore

            yaml.safe_dump([route.to_dict() for route in routes], dest.open("w", encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "PyYAML is required for YAML export. Install API extras: pip install -e .[api]"
            ) from exc
    elif format == "json":
        dest.write_text(json.dumps([route.to_dict() for route in routes], indent=2), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported format: {format}")
