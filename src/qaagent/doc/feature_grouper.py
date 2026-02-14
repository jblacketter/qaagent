"""Groups routes into feature areas by tag or path prefix."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import List

from ..analyzers.models import Route
from .models import FeatureArea, RouteDoc

# HTTP method → CRUD operation mapping
_METHOD_CRUD: dict[str, str] = {
    "POST": "create",
    "GET": "read",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


def _route_to_doc(route: Route) -> RouteDoc:
    """Convert an analyzers Route to a RouteDoc."""
    return RouteDoc(
        path=route.path,
        method=route.method,
        summary=route.summary,
        description=route.description,
        auth_required=route.auth_required,
        params=route.params,
        responses=route.responses,
        tags=list(route.tags),
    )


def _extract_prefix(path: str) -> str:
    """Extract the first meaningful path segment as a grouping prefix.

    Examples:
        /api/v1/users/{id}  → users
        /users              → users
        /api/users          → users
        /health             → health
    """
    # Strip leading slash, split segments
    segments = [s for s in path.strip("/").split("/") if s]
    # Skip common prefixes like 'api', 'v1', 'v2', etc.
    skip = {"api", "v1", "v2", "v3"}
    for seg in segments:
        if seg in skip:
            continue
        # Stop at path params
        if seg.startswith("{"):
            break
        return seg
    return "root"


def _slugify(text: str) -> str:
    """Convert text to a safe slug ID."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "unknown"


def group_routes(routes: List[Route]) -> List[FeatureArea]:
    """Group routes into feature areas.

    Strategy:
    1. If routes have tags, group by the first tag (primary tag grouping).
    2. If no tags, fall back to path prefix grouping.
    """
    tagged: dict[str, list[Route]] = defaultdict(list)
    untagged: list[Route] = []

    for route in routes:
        if route.tags:
            # Use first tag as primary grouping key
            tagged[route.tags[0]].append(route)
        else:
            untagged.append(route)

    # Group untagged routes by path prefix
    prefix_groups: dict[str, list[Route]] = defaultdict(list)
    for route in untagged:
        prefix = _extract_prefix(route.path)
        prefix_groups[prefix].append(route)

    # Merge tagged and prefix groups that share the same slug to avoid
    # duplicate feature IDs (e.g. tagged "users" + untagged /users/{id}).
    merged: dict[str, list[Route]] = defaultdict(list)
    merged_names: dict[str, str] = {}

    for tag, tag_routes in sorted(tagged.items()):
        slug = _slugify(tag)
        merged[slug].extend(tag_routes)
        merged_names.setdefault(slug, tag)

    for prefix, prefix_routes in sorted(prefix_groups.items()):
        slug = _slugify(prefix)
        merged[slug].extend(prefix_routes)
        merged_names.setdefault(slug, prefix)

    # Build feature areas from merged groups
    features: list[FeatureArea] = []
    for slug in sorted(merged):
        feature = _build_feature(merged_names[slug], merged[slug])
        features.append(feature)

    return features


def _build_feature(name: str, routes: List[Route]) -> FeatureArea:
    """Build a FeatureArea from a group of routes."""
    route_docs = [_route_to_doc(r) for r in routes]

    # Detect CRUD operations
    crud_ops = set()
    for route in routes:
        op = _METHOD_CRUD.get(route.method.upper())
        if op:
            crud_ops.add(op)

    # Aggregate auth: feature requires auth if any route does
    any_auth = any(r.auth_required for r in routes)

    # Collect all tags across routes
    all_tags = set()
    for route in routes:
        all_tags.update(route.tags)

    display_name = name.replace("-", " ").replace("_", " ").title()

    return FeatureArea(
        id=_slugify(name),
        name=display_name,
        routes=route_docs,
        crud_operations=sorted(crud_ops),
        auth_required=any_auth,
        tags=sorted(all_tags),
    )
