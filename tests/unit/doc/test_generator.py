"""Tests for documentation generator orchestrator."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from qaagent.analyzers.models import Route, RouteSource
from qaagent.doc.generator import (
    generate_documentation,
    save_documentation,
    load_documentation,
    _compute_content_hash,
)
from qaagent.doc.models import AppDocumentation, Integration, IntegrationType


def _make_routes():
    """Create a set of test routes."""
    return [
        Route(
            path="/api/users",
            method="GET",
            auth_required=True,
            tags=["users"],
            summary="List users",
            source=RouteSource.OPENAPI,
        ),
        Route(
            path="/api/users",
            method="POST",
            auth_required=True,
            tags=["users"],
            summary="Create user",
            source=RouteSource.OPENAPI,
        ),
        Route(
            path="/api/users/{id}",
            method="GET",
            auth_required=True,
            tags=["users"],
            summary="Get user",
            source=RouteSource.OPENAPI,
        ),
        Route(
            path="/api/users/{id}",
            method="PUT",
            auth_required=True,
            tags=["users"],
            summary="Update user",
            source=RouteSource.OPENAPI,
        ),
        Route(
            path="/api/users/{id}",
            method="DELETE",
            auth_required=True,
            tags=["users"],
            summary="Delete user",
            source=RouteSource.OPENAPI,
        ),
        Route(
            path="/api/orders",
            method="GET",
            auth_required=False,
            tags=["orders"],
            summary="List orders",
            source=RouteSource.OPENAPI,
        ),
        Route(
            path="/health",
            method="GET",
            auth_required=False,
            summary="Health check",
            source=RouteSource.OPENAPI,
        ),
    ]


class TestGenerateDocumentation:
    def test_with_provided_routes(self):
        routes = _make_routes()
        doc = generate_documentation(
            routes=routes,
            app_name="Test App",
            use_llm=False,
        )
        assert doc.app_name == "Test App"
        assert doc.total_routes == 7
        assert len(doc.features) > 0
        assert doc.summary  # template synthesis should produce a summary

    def test_feature_grouping(self):
        routes = _make_routes()
        doc = generate_documentation(
            routes=routes,
            app_name="Test",
            use_llm=False,
        )
        feature_ids = {f.id for f in doc.features}
        assert "users" in feature_ids
        assert "orders" in feature_ids

    def test_users_feature_has_full_crud(self):
        routes = _make_routes()
        doc = generate_documentation(
            routes=routes,
            app_name="Test",
            use_llm=False,
        )
        users = next(f for f in doc.features if f.id == "users")
        assert users.has_full_crud
        assert users.auth_required

    def test_no_routes_produces_empty_doc(self):
        doc = generate_documentation(
            routes=[],
            app_name="Empty",
            use_llm=False,
        )
        assert doc.total_routes == 0
        assert doc.features == []

    def test_content_hash_set(self):
        routes = _make_routes()
        doc = generate_documentation(
            routes=routes,
            app_name="Test",
            use_llm=False,
        )
        assert doc.content_hash
        assert len(doc.content_hash) == 16

    def test_generated_at_set(self):
        doc = generate_documentation(
            routes=[],
            app_name="Test",
            use_llm=False,
        )
        assert doc.generated_at

    def test_integration_detection(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("import redis\nimport stripe\n")

        doc = generate_documentation(
            routes=_make_routes(),
            source_dir=src,
            app_name="Test",
            use_llm=False,
        )
        int_names = {i.name for i in doc.integrations}
        assert "Redis" in int_names
        assert "Stripe" in int_names

    @patch("qaagent.doc.generator.discover_routes")
    def test_discovers_routes_when_not_provided(self, mock_discover):
        mock_discover.return_value = _make_routes()
        doc = generate_documentation(
            source_dir=Path("/fake"),
            app_name="Auto",
            use_llm=False,
        )
        mock_discover.assert_called_once()
        assert doc.total_routes == 7


class TestSaveAndLoad:
    def test_save_creates_file(self, tmp_path):
        doc = AppDocumentation(app_name="Save Test", total_routes=3)
        output = save_documentation(doc, tmp_path)
        assert output.exists()
        assert output.name == "appdoc.json"
        assert (tmp_path / ".qaagent").is_dir()

    def test_save_creates_qaagent_dir(self, tmp_path):
        doc = AppDocumentation(app_name="Test")
        save_documentation(doc, tmp_path)
        assert (tmp_path / ".qaagent").is_dir()

    def test_load_roundtrip(self, tmp_path):
        doc = AppDocumentation(
            app_name="Round Trip",
            summary="Test summary",
            total_routes=5,
        )
        save_documentation(doc, tmp_path)
        loaded = load_documentation(tmp_path)
        assert loaded is not None
        assert loaded.app_name == "Round Trip"
        assert loaded.summary == "Test summary"
        assert loaded.total_routes == 5

    def test_load_nonexistent(self, tmp_path):
        loaded = load_documentation(tmp_path)
        assert loaded is None

    def test_load_invalid_json(self, tmp_path):
        qaagent_dir = tmp_path / ".qaagent"
        qaagent_dir.mkdir()
        (qaagent_dir / "appdoc.json").write_text("not valid json")
        loaded = load_documentation(tmp_path)
        assert loaded is None

    def test_full_roundtrip_with_features(self, tmp_path):
        routes = _make_routes()
        doc = generate_documentation(
            routes=routes,
            app_name="Full Test",
            use_llm=False,
        )
        save_documentation(doc, tmp_path)
        loaded = load_documentation(tmp_path)
        assert loaded is not None
        assert loaded.app_name == "Full Test"
        assert loaded.total_routes == 7
        assert len(loaded.features) == len(doc.features)


class TestContentHash:
    def test_same_input_same_hash(self):
        routes = _make_routes()
        h1 = _compute_content_hash(routes, [])
        h2 = _compute_content_hash(routes, [])
        assert h1 == h2

    def test_different_routes_different_hash(self):
        r1 = [Route(path="/a", method="GET", auth_required=False)]
        r2 = [Route(path="/b", method="GET", auth_required=False)]
        h1 = _compute_content_hash(r1, [])
        h2 = _compute_content_hash(r2, [])
        assert h1 != h2

    def test_integrations_affect_hash(self):
        routes = _make_routes()
        i1 = [Integration(id="redis", name="Redis", type=IntegrationType.DATABASE)]
        h1 = _compute_content_hash(routes, [])
        h2 = _compute_content_hash(routes, i1)
        assert h1 != h2

    def test_hash_order_independent(self):
        """Hash should be the same regardless of route/integration order."""
        r1 = Route(path="/a", method="GET", auth_required=False)
        r2 = Route(path="/b", method="POST", auth_required=False)
        i1 = Integration(id="redis", name="Redis", type=IntegrationType.DATABASE)
        i2 = Integration(id="stripe", name="Stripe", type=IntegrationType.SDK)
        h_forward = _compute_content_hash([r1, r2], [i1, i2])
        h_reverse = _compute_content_hash([r2, r1], [i2, i1])
        assert h_forward == h_reverse
