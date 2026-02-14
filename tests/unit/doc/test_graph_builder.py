"""Tests for graph builder."""

import pytest
from qaagent.doc.graph_builder import (
    build_feature_map,
    build_integration_map,
    build_route_graph,
    build_all_graphs,
)
from qaagent.doc.models import (
    AppDocumentation,
    FeatureArea,
    Integration,
    IntegrationType,
    RouteDoc,
)


def _make_doc(**overrides):
    defaults = dict(
        app_name="Test",
        total_routes=0,
        features=[],
        integrations=[],
    )
    defaults.update(overrides)
    return AppDocumentation(**defaults)


class TestBuildFeatureMap:
    def test_creates_feature_nodes(self):
        doc = _make_doc(features=[
            FeatureArea(id="users", name="Users", routes=[
                RouteDoc(path="/users", method="GET"),
            ]),
            FeatureArea(id="orders", name="Orders", routes=[
                RouteDoc(path="/orders", method="GET"),
            ]),
        ])
        nodes, edges = build_feature_map(doc)
        assert len(nodes) == 2
        assert nodes[0].id == "feat-users"
        assert nodes[0].type == "feature"
        assert nodes[1].id == "feat-orders"

    def test_shared_integration_edge(self):
        doc = _make_doc(
            features=[
                FeatureArea(id="users", name="Users"),
                FeatureArea(id="orders", name="Orders"),
            ],
            integrations=[
                Integration(
                    id="redis",
                    name="Redis",
                    type=IntegrationType.DATABASE,
                    connected_features=["users", "orders"],
                ),
            ],
        )
        nodes, edges = build_feature_map(doc)
        assert len(edges) == 1
        assert edges[0].type == "shared_integration"

    def test_no_edges_for_single_connection(self):
        doc = _make_doc(
            features=[FeatureArea(id="users", name="Users")],
            integrations=[
                Integration(
                    id="redis",
                    name="Redis",
                    type=IntegrationType.DATABASE,
                    connected_features=["users"],
                ),
            ],
        )
        _, edges = build_feature_map(doc)
        assert len(edges) == 0

    def test_empty_doc(self):
        doc = _make_doc()
        nodes, edges = build_feature_map(doc)
        assert nodes == []
        assert edges == []


class TestBuildIntegrationMap:
    def test_creates_both_node_types(self):
        doc = _make_doc(
            features=[FeatureArea(id="users", name="Users")],
            integrations=[
                Integration(
                    id="redis",
                    name="Redis",
                    type=IntegrationType.DATABASE,
                ),
            ],
        )
        nodes, edges = build_integration_map(doc)
        feature_nodes = [n for n in nodes if n.type == "feature"]
        int_nodes = [n for n in nodes if n.type == "integration"]
        assert len(feature_nodes) == 1
        assert len(int_nodes) == 1

    def test_creates_connection_edges(self):
        doc = _make_doc(
            features=[
                FeatureArea(id="users", name="Users"),
                FeatureArea(id="orders", name="Orders"),
            ],
            integrations=[
                Integration(
                    id="redis",
                    name="Redis",
                    type=IntegrationType.DATABASE,
                    connected_features=["users", "orders"],
                ),
            ],
        )
        _, edges = build_integration_map(doc)
        assert len(edges) == 2  # redis → users, redis → orders

    def test_integration_metadata(self):
        doc = _make_doc(integrations=[
            Integration(
                id="stripe",
                name="Stripe",
                type=IntegrationType.SDK,
                package="stripe",
                env_vars=["STRIPE_KEY"],
            ),
        ])
        nodes, _ = build_integration_map(doc)
        int_node = next(n for n in nodes if n.type == "integration")
        assert int_node.metadata["integration_type"] == "sdk"
        assert int_node.metadata["env_vars"] == ["STRIPE_KEY"]
        assert int_node.metadata["package"] == "stripe"

    def test_position_layout(self):
        doc = _make_doc(
            features=[FeatureArea(id="a", name="A"), FeatureArea(id="b", name="B")],
            integrations=[Integration(id="r", name="R", type=IntegrationType.DATABASE)],
        )
        nodes, _ = build_integration_map(doc)
        feature_nodes = [n for n in nodes if n.type == "feature"]
        int_nodes = [n for n in nodes if n.type == "integration"]
        # Features should be on the left, integrations on the right
        assert all(n.position["x"] < 300 for n in feature_nodes)
        assert all(n.position["x"] > 300 for n in int_nodes)


class TestBuildRouteGraph:
    def test_creates_route_group_nodes(self):
        doc = _make_doc(features=[
            FeatureArea(id="users", name="Users", routes=[
                RouteDoc(path="/users", method="GET"),
                RouteDoc(path="/users/{id}", method="GET"),
            ]),
        ])
        nodes, edges = build_route_graph(doc)
        assert any(n.label == "/users" for n in nodes)

    def test_parent_child_edges(self):
        doc = _make_doc(features=[
            FeatureArea(id="users", name="Users", routes=[
                RouteDoc(path="/users/{id}/orders", method="GET"),
            ]),
        ])
        nodes, edges = build_route_graph(doc)
        # Should have users → orders parent-child edge
        node_ids = {n.id for n in nodes}
        assert "rg-users" in node_ids
        assert "rg-users/orders" in node_ids
        parent_child = [e for e in edges if e.type == "parent_child"]
        assert len(parent_child) >= 1

    def test_skips_api_prefix(self):
        doc = _make_doc(features=[
            FeatureArea(id="users", name="Users", routes=[
                RouteDoc(path="/api/v1/users", method="GET"),
            ]),
        ])
        nodes, _ = build_route_graph(doc)
        labels = {n.label for n in nodes}
        assert "/users" in labels
        assert "/api" not in labels

    def test_empty_routes(self):
        doc = _make_doc(features=[
            FeatureArea(id="empty", name="Empty"),
        ])
        nodes, edges = build_route_graph(doc)
        assert nodes == []
        assert edges == []


class TestBuildAllGraphs:
    def test_attaches_to_doc(self):
        doc = _make_doc(
            features=[
                FeatureArea(id="users", name="Users", routes=[
                    RouteDoc(path="/users", method="GET"),
                ]),
            ],
            integrations=[
                Integration(id="redis", name="Redis", type=IntegrationType.DATABASE),
            ],
        )
        result = build_all_graphs(doc)
        assert len(result.architecture_nodes) > 0
        assert any("feature_map" in (n.metadata.get("graph_type", "")) for n in result.architecture_nodes)
        assert any("integration_map" in (n.metadata.get("graph_type", "")) for n in result.architecture_nodes)

    def test_edge_types_prefixed(self):
        doc = _make_doc(
            features=[
                FeatureArea(id="a", name="A"),
                FeatureArea(id="b", name="B"),
            ],
            integrations=[
                Integration(
                    id="redis",
                    name="Redis",
                    type=IntegrationType.DATABASE,
                    connected_features=["a", "b"],
                ),
            ],
        )
        result = build_all_graphs(doc)
        edge_types = {e.type for e in result.architecture_edges}
        assert any(t.startswith("feature_map:") for t in edge_types)
        assert any(t.startswith("integration_map:") for t in edge_types)


class TestPathMatchesPrefix:
    def test_simple_match(self):
        from qaagent.doc.graph_builder import _path_matches_prefix
        assert _path_matches_prefix("/users/{id}", "/users") is True

    def test_no_match(self):
        from qaagent.doc.graph_builder import _path_matches_prefix
        assert _path_matches_prefix("/orders/123", "/users") is False

    def test_param_does_not_wildcard_match_other_prefix(self):
        """Path params should not match as wildcards against different prefix segments."""
        from qaagent.doc.graph_builder import _path_matches_prefix
        assert _path_matches_prefix("/users/{id}/profile", "/users/orders") is False

    def test_nested_match(self):
        from qaagent.doc.graph_builder import _path_matches_prefix
        assert _path_matches_prefix("/users/{id}/profile", "/users") is True
