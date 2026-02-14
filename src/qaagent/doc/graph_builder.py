"""Builds architecture graph nodes and edges from AppDocumentation.

Produces three diagram types:
1. Feature Map — feature-to-feature relationships via shared integrations
2. Integration Map — features ↔ external services
3. Route Graph — route hierarchy by prefix
"""

from __future__ import annotations

import re
from typing import List

from .models import (
    AppDocumentation,
    ArchitectureEdge,
    ArchitectureNode,
    FeatureArea,
    Integration,
)

# Layout constants
_FEATURE_Y_SPACING = 120
_INTEGRATION_Y_SPACING = 120
_LEFT_X = 100
_RIGHT_X = 500
_CENTER_X = 300


def build_feature_map(doc: AppDocumentation) -> tuple[list[ArchitectureNode], list[ArchitectureEdge]]:
    """Build Feature Map: nodes = features, edges = shared integrations or overlapping prefixes."""
    nodes: list[ArchitectureNode] = []
    edges: list[ArchitectureEdge] = []
    edge_set: set[tuple[str, str]] = set()

    for i, feature in enumerate(doc.features):
        nodes.append(ArchitectureNode(
            id=f"feat-{feature.id}",
            label=feature.name,
            type="feature",
            metadata={
                "route_count": feature.route_count,
                "crud_operations": feature.crud_operations,
                "auth_required": feature.auth_required,
            },
            position={"x": _CENTER_X, "y": i * _FEATURE_Y_SPACING},
        ))

    # Create edges for features sharing integrations
    for integration in doc.integrations:
        connected = integration.connected_features
        if len(connected) < 2:
            continue
        for j in range(len(connected)):
            for k in range(j + 1, len(connected)):
                pair = tuple(sorted([connected[j], connected[k]]))
                if pair not in edge_set:
                    edge_set.add(pair)
                    edges.append(ArchitectureEdge(
                        id=f"shared-{pair[0]}-{pair[1]}",
                        source=f"feat-{pair[0]}",
                        target=f"feat-{pair[1]}",
                        label=f"via {integration.name}",
                        type="shared_integration",
                    ))

    # Create edges for features with overlapping route prefixes
    prefixes: dict[str, list[str]] = {}
    for feature in doc.features:
        for route in feature.routes:
            segments = [
                s for s in route.path.strip("/").split("/")
                if s and not s.startswith("{") and s != "api" and not re.fullmatch(r"v\d+", s)
            ]
            prefix = segments[0] if segments else "root"
            prefixes.setdefault(prefix, [])
            if feature.id not in prefixes[prefix]:
                prefixes[prefix].append(feature.id)

    for prefix, feature_ids in prefixes.items():
        if len(feature_ids) < 2:
            continue
        for j in range(len(feature_ids)):
            for k in range(j + 1, len(feature_ids)):
                pair = tuple(sorted([feature_ids[j], feature_ids[k]]))
                if pair not in edge_set:
                    edge_set.add(pair)
                    edges.append(ArchitectureEdge(
                        id=f"prefix-{pair[0]}-{pair[1]}",
                        source=f"feat-{pair[0]}",
                        target=f"feat-{pair[1]}",
                        label=f"/{prefix}",
                        type="shared_prefix",
                    ))

    return nodes, edges


def build_integration_map(doc: AppDocumentation) -> tuple[list[ArchitectureNode], list[ArchitectureEdge]]:
    """Build Integration Map: feature nodes (left) ↔ integration nodes (right)."""
    nodes: list[ArchitectureNode] = []
    edges: list[ArchitectureEdge] = []

    # Feature nodes on the left
    for i, feature in enumerate(doc.features):
        nodes.append(ArchitectureNode(
            id=f"feat-{feature.id}",
            label=feature.name,
            type="feature",
            metadata={
                "route_count": feature.route_count,
                "crud_operations": feature.crud_operations,
                "auth_required": feature.auth_required,
            },
            position={"x": _LEFT_X, "y": i * _FEATURE_Y_SPACING},
        ))

    # Integration nodes on the right
    for i, integration in enumerate(doc.integrations):
        nodes.append(ArchitectureNode(
            id=f"int-{integration.id}",
            label=integration.name,
            type="integration",
            metadata={
                "integration_type": integration.type.value,
                "env_vars": integration.env_vars,
                "package": integration.package,
            },
            position={"x": _RIGHT_X, "y": i * _INTEGRATION_Y_SPACING},
        ))

        # Create edges from integration to connected features
        for feat_id in integration.connected_features:
            edges.append(ArchitectureEdge(
                id=f"conn-{integration.id}-{feat_id}",
                source=f"feat-{feat_id}",
                target=f"int-{integration.id}",
                label=integration.type.value,
                type="connection",
            ))

    return nodes, edges


def build_route_graph(doc: AppDocumentation) -> tuple[list[ArchitectureNode], list[ArchitectureEdge]]:
    """Build Route Graph: route groups by prefix with parent-child edges."""
    nodes: list[ArchitectureNode] = []
    edges: list[ArchitectureEdge] = []
    node_ids: set[str] = set()

    # Collect all route paths and group by prefix hierarchy
    for feature in doc.features:
        for route in feature.routes:
            segments = [
                s for s in route.path.strip("/").split("/")
                if s and s != "api" and not re.fullmatch(r"v\d+", s) and not s.startswith("{")
            ]
            if not segments:
                continue

            # Create nodes for each level of the path hierarchy
            for depth in range(len(segments)):
                path_prefix = "/".join(segments[: depth + 1])
                node_id = f"rg-{path_prefix}"

                if node_id not in node_ids:
                    node_ids.add(node_id)
                    # Count routes matching this prefix
                    prefix_path = "/" + path_prefix
                    route_count = sum(
                        1 for f in doc.features for r in f.routes
                        if _path_matches_prefix(r.path, prefix_path)
                    )
                    nodes.append(ArchitectureNode(
                        id=node_id,
                        label=f"/{path_prefix}",
                        type="route_group",
                        metadata={
                            "route_count": route_count,
                            "depth": depth,
                        },
                        position={"x": depth * 200, "y": len(nodes) * 80},
                    ))

                # Create parent-child edge
                if depth > 0:
                    parent_prefix = "/".join(segments[: depth])
                    parent_id = f"rg-{parent_prefix}"
                    edge_id = f"rg-edge-{parent_prefix}-{path_prefix}"
                    if parent_id in node_ids and not any(e.id == edge_id for e in edges):
                        edges.append(ArchitectureEdge(
                            id=edge_id,
                            source=parent_id,
                            target=node_id,
                            type="parent_child",
                        ))

    return nodes, edges


def _path_matches_prefix(path: str, prefix: str) -> bool:
    """Check if a path starts with a given prefix, ignoring api/version segments.

    Path param segments (e.g. {id}) in the path are skipped during comparison
    rather than treated as wildcards, so /users/{id}/profile does NOT match
    the prefix /users/orders.
    """
    path_segs = [s for s in path.strip("/").split("/") if s != "api" and not re.fullmatch(r"v\d+", s)]
    prefix_segs = [s for s in prefix.strip("/").split("/") if s != "api" and not re.fullmatch(r"v\d+", s)]

    # Filter out path param segments from the path for comparison
    path_static = [s for s in path_segs if not s.startswith("{")]

    if len(path_static) < len(prefix_segs):
        return False

    for ps, xs in zip(prefix_segs, path_static):
        if ps != xs:
            return False

    return True


def build_all_graphs(doc: AppDocumentation) -> AppDocumentation:
    """Build all three graph types and attach to the documentation."""
    nodes: list[ArchitectureNode] = []
    edges: list[ArchitectureEdge] = []

    fm_nodes, fm_edges = build_feature_map(doc)
    im_nodes, im_edges = build_integration_map(doc)
    rg_nodes, rg_edges = build_route_graph(doc)

    # Tag each with a graph_type in metadata
    for n in fm_nodes:
        n.metadata["graph_type"] = "feature_map"
    for e in fm_edges:
        e.type = f"feature_map:{e.type}"

    for n in im_nodes:
        n.metadata["graph_type"] = "integration_map"
    for e in im_edges:
        e.type = f"integration_map:{e.type}"

    for n in rg_nodes:
        n.metadata["graph_type"] = "route_graph"
    for e in rg_edges:
        e.type = f"route_graph:{e.type}"

    nodes = fm_nodes + im_nodes + rg_nodes
    edges = fm_edges + im_edges + rg_edges

    doc.architecture_nodes = nodes
    doc.architecture_edges = edges
    return doc
