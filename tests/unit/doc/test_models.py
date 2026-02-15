"""Tests for doc models serialization and validation."""

import pytest
from qaagent.doc.models import (
    AppDocumentation,
    ArchitectureEdge,
    ArchitectureNode,
    CujStep,
    DiscoveredCUJ,
    FeatureArea,
    Integration,
    IntegrationType,
    RouteDoc,
)


class TestRouteDoc:
    def test_basic_creation(self):
        rd = RouteDoc(path="/users", method="GET")
        assert rd.path == "/users"
        assert rd.method == "GET"
        assert rd.auth_required is False
        assert rd.params == {}
        assert rd.tags == []

    def test_full_creation(self):
        rd = RouteDoc(
            path="/users/{id}",
            method="PUT",
            summary="Update user",
            description="Update a user by ID",
            auth_required=True,
            params={"path": {"id": "int"}},
            responses={"200": {"description": "OK"}},
            tags=["users"],
        )
        assert rd.auth_required is True
        assert rd.tags == ["users"]

    def test_roundtrip(self):
        rd = RouteDoc(path="/test", method="POST", auth_required=True, tags=["a"])
        data = rd.model_dump()
        rd2 = RouteDoc.model_validate(data)
        assert rd == rd2


class TestFeatureArea:
    def test_basic(self):
        fa = FeatureArea(id="users", name="Users")
        assert fa.route_count == 0
        assert fa.has_full_crud is False

    def test_crud_detection(self):
        fa = FeatureArea(
            id="users",
            name="Users",
            crud_operations=["create", "read", "update", "delete"],
        )
        assert fa.has_full_crud is True

    def test_partial_crud(self):
        fa = FeatureArea(
            id="users",
            name="Users",
            crud_operations=["read", "create"],
        )
        assert fa.has_full_crud is False

    def test_route_count(self):
        fa = FeatureArea(
            id="users",
            name="Users",
            routes=[
                RouteDoc(path="/users", method="GET"),
                RouteDoc(path="/users", method="POST"),
            ],
        )
        assert fa.route_count == 2

    def test_roundtrip(self):
        fa = FeatureArea(
            id="users",
            name="Users",
            description="User management",
            routes=[RouteDoc(path="/users", method="GET")],
            crud_operations=["read"],
            auth_required=True,
            integration_ids=["stripe"],
            tags=["users"],
        )
        data = fa.model_dump()
        fa2 = FeatureArea.model_validate(data)
        assert fa2.id == fa.id
        assert fa2.routes == fa.routes
        assert fa2.auth_required is True


class TestIntegration:
    def test_basic(self):
        i = Integration(id="stripe", name="Stripe", type=IntegrationType.SDK)
        assert i.type == IntegrationType.SDK
        assert i.source == "auto"

    def test_all_types(self):
        for itype in IntegrationType:
            i = Integration(id="test", name="Test", type=itype)
            assert i.type == itype

    def test_roundtrip(self):
        i = Integration(
            id="redis",
            name="Redis",
            type=IntegrationType.DATABASE,
            package="redis",
            env_vars=["REDIS_URL", "REDIS_PORT"],
            connected_features=["cache", "sessions"],
            source="auto",
        )
        data = i.model_dump()
        i2 = Integration.model_validate(data)
        assert i2.env_vars == ["REDIS_URL", "REDIS_PORT"]
        assert i2.type == IntegrationType.DATABASE


class TestDiscoveredCUJ:
    def test_basic(self):
        cuj = DiscoveredCUJ(id="login-flow", name="Login Flow", pattern="auth_flow")
        assert cuj.steps == []
        assert cuj.confidence == 1.0

    def test_with_steps(self):
        cuj = DiscoveredCUJ(
            id="crud-users",
            name="User CRUD",
            pattern="crud_lifecycle",
            steps=[
                CujStep(order=1, action="Create user", route="/users", method="POST"),
                CujStep(order=2, action="Read user", route="/users/{id}", method="GET"),
            ],
        )
        assert len(cuj.steps) == 2
        assert cuj.steps[0].method == "POST"

    def test_roundtrip(self):
        cuj = DiscoveredCUJ(
            id="test",
            name="Test",
            steps=[CujStep(order=1, action="Do thing")],
        )
        data = cuj.model_dump()
        cuj2 = DiscoveredCUJ.model_validate(data)
        assert cuj2.steps[0].action == "Do thing"


class TestArchitectureModels:
    def test_node(self):
        node = ArchitectureNode(
            id="n1", label="Users", type="feature",
            metadata={"route_count": 5},
        )
        assert node.position is None
        data = node.model_dump()
        assert data["metadata"]["route_count"] == 5

    def test_edge(self):
        edge = ArchitectureEdge(id="e1", source="n1", target="n2", label="uses")
        assert edge.type == "default"

    def test_roundtrip(self):
        node = ArchitectureNode(id="n1", label="Test", type="integration")
        edge = ArchitectureEdge(id="e1", source="n1", target="n2")
        nd = ArchitectureNode.model_validate(node.model_dump())
        ed = ArchitectureEdge.model_validate(edge.model_dump())
        assert nd.id == "n1"
        assert ed.source == "n1"


class TestAppDocumentation:
    def test_minimal(self):
        doc = AppDocumentation(app_name="Test App")
        assert doc.app_name == "Test App"
        assert doc.features == []
        assert doc.integrations == []
        assert doc.total_routes == 0
        assert doc.generated_at  # should have a timestamp

    def test_full(self):
        doc = AppDocumentation(
            app_name="My App",
            summary="A test application",
            content_hash="abc123",
            source_dir="/src",
            features=[
                FeatureArea(id="users", name="Users"),
            ],
            integrations=[
                Integration(id="stripe", name="Stripe", type=IntegrationType.SDK),
            ],
            discovered_cujs=[
                DiscoveredCUJ(id="login", name="Login"),
            ],
            architecture_nodes=[
                ArchitectureNode(id="n1", label="Users", type="feature"),
            ],
            architecture_edges=[
                ArchitectureEdge(id="e1", source="n1", target="n2"),
            ],
            total_routes=10,
            metadata={"version": "1.0"},
        )
        assert len(doc.features) == 1
        assert len(doc.integrations) == 1

    def test_roundtrip(self):
        doc = AppDocumentation(
            app_name="Test",
            features=[
                FeatureArea(
                    id="users",
                    name="Users",
                    routes=[RouteDoc(path="/users", method="GET")],
                ),
            ],
            integrations=[
                Integration(id="redis", name="Redis", type=IntegrationType.DATABASE),
            ],
            total_routes=1,
        )
        data = doc.model_dump()
        doc2 = AppDocumentation.model_validate(data)
        assert doc2.app_name == "Test"
        assert doc2.features[0].routes[0].path == "/users"
        assert doc2.integrations[0].type == IntegrationType.DATABASE

    def test_json_roundtrip(self):
        doc = AppDocumentation(app_name="JSON Test", total_routes=5)
        json_str = doc.model_dump_json()
        doc2 = AppDocumentation.model_validate_json(json_str)
        assert doc2.app_name == "JSON Test"
        assert doc2.total_routes == 5
