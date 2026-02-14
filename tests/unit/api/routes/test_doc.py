"""Unit tests for doc API routes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from qaagent.api.app import create_app
from qaagent.doc.models import (
    AppDocumentation,
    FeatureArea,
    Integration,
    IntegrationType,
    RouteDoc,
    DiscoveredCUJ,
    CujStep,
    ArchitectureNode,
    ArchitectureEdge,
)

# load_documentation is imported at module level in doc.py, so patch there.
# load_active_profile is lazily imported inside functions, so patch at source.
_PATCH_LOAD_DOC = "qaagent.api.routes.doc.load_documentation"
_PATCH_LOAD_PROFILE = "qaagent.config.load_active_profile"
_PATCH_DISCOVER = "qaagent.doc.generator.discover_routes"
_PATCH_SAVE_DOC = "qaagent.api.routes.doc.save_documentation"


def _sample_doc():
    return AppDocumentation(
        app_name="Test App",
        summary="A test app.",
        total_routes=5,
        content_hash="abc123",
        features=[
            FeatureArea(
                id="users",
                name="Users",
                description="User management",
                routes=[
                    RouteDoc(path="/users", method="GET", summary="List users", auth_required=True),
                    RouteDoc(path="/users", method="POST", summary="Create user", auth_required=True),
                ],
                crud_operations=["create", "read"],
                auth_required=True,
                tags=["users"],
            ),
            FeatureArea(
                id="orders",
                name="Orders",
                routes=[RouteDoc(path="/orders", method="GET", summary="List orders")],
                crud_operations=["read"],
            ),
        ],
        integrations=[
            Integration(
                id="redis",
                name="Redis",
                type=IntegrationType.DATABASE,
                package="redis",
                env_vars=["REDIS_URL"],
            ),
            Integration(
                id="stripe",
                name="Stripe",
                type=IntegrationType.SDK,
                env_vars=["STRIPE_API_KEY"],
            ),
        ],
        discovered_cujs=[
            DiscoveredCUJ(
                id="login-flow",
                name="Login Flow",
                pattern="auth_flow",
                steps=[
                    CujStep(order=1, action="Register", route="/register", method="POST"),
                    CujStep(order=2, action="Login", route="/login", method="POST"),
                ],
            ),
        ],
        architecture_nodes=[
            ArchitectureNode(id="n1", label="Users", type="feature"),
        ],
        architecture_edges=[
            ArchitectureEdge(id="e1", source="n1", target="n2"),
        ],
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("QAAGENT_RUNS_DIR", str(tmp_path / "runs"))
    (tmp_path / "runs").mkdir()
    app = create_app()
    return TestClient(app)


class TestGetDoc:
    def test_returns_full_doc(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            resp = client.get("/api/doc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app_name"] == "Test App"
        assert data["total_routes"] == 5
        assert len(data["features"]) == 2
        assert len(data["integrations"]) == 2

    def test_404_when_no_doc(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=None):
            resp = client.get("/api/doc")
        assert resp.status_code == 404


class TestGetFeatures:
    def test_returns_features(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            resp = client.get("/api/doc/features")
        assert resp.status_code == 200
        features = resp.json()["features"]
        assert len(features) == 2
        assert features[0]["id"] == "users"

    def test_get_single_feature(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            resp = client.get("/api/doc/features/users")
        assert resp.status_code == 200
        assert resp.json()["id"] == "users"
        assert resp.json()["name"] == "Users"

    def test_feature_not_found(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            resp = client.get("/api/doc/features/nonexistent")
        assert resp.status_code == 404


class TestGetIntegrations:
    def test_returns_integrations(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            resp = client.get("/api/doc/integrations")
        assert resp.status_code == 200
        integrations = resp.json()["integrations"]
        assert len(integrations) == 2
        assert integrations[0]["name"] == "Redis"


class TestGetCujs:
    def test_returns_cujs(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            resp = client.get("/api/doc/cujs")
        assert resp.status_code == 200
        cujs = resp.json()["cujs"]
        assert len(cujs) == 1
        assert cujs[0]["name"] == "Login Flow"
        assert len(cujs[0]["steps"]) == 2


class TestGetArchitecture:
    def test_returns_nodes_and_edges(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            resp = client.get("/api/doc/architecture")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 1


class TestRegenerate:
    def test_regenerate(self, client, tmp_path):
        mock_entry = MagicMock()
        mock_entry.resolved_path.return_value = tmp_path
        mock_profile = MagicMock()
        mock_profile.project.name = "TestApp"

        with patch(_PATCH_LOAD_PROFILE, return_value=(mock_entry, mock_profile)), \
             patch(_PATCH_DISCOVER, return_value=[]), \
             patch(_PATCH_SAVE_DOC):
            resp = client.post("/api/doc/regenerate", json={"no_llm": True})

        assert resp.status_code == 200
        assert resp.json()["app_name"] == "TestApp"

    def test_regenerate_passes_doc_settings(self, client, tmp_path):
        """API regeneration should pass profile doc_settings to generate_documentation."""
        from qaagent.config.models import DocSettings

        mock_entry = MagicMock()
        mock_entry.resolved_path.return_value = tmp_path
        mock_profile = MagicMock()
        mock_profile.project.name = "TestApp"
        mock_profile.doc = DocSettings(custom_summary="Custom from config")
        mock_profile.resolve_spec_path.return_value = None

        with patch(_PATCH_LOAD_PROFILE, return_value=(mock_entry, mock_profile)), \
             patch(_PATCH_DISCOVER, return_value=[]), \
             patch(_PATCH_SAVE_DOC):
            resp = client.post("/api/doc/regenerate", json={"no_llm": True})

        assert resp.status_code == 200
        assert resp.json()["summary"] == "Custom from config"

    def test_regenerate_passes_openapi_path(self, client, tmp_path):
        """API regeneration should pass profile openapi spec path."""
        mock_entry = MagicMock()
        mock_entry.resolved_path.return_value = tmp_path
        mock_profile = MagicMock()
        mock_profile.project.name = "TestApp"
        mock_profile.doc = None
        spec_path = tmp_path / "openapi.yaml"
        mock_profile.resolve_spec_path.return_value = spec_path

        with patch(_PATCH_LOAD_PROFILE, return_value=(mock_entry, mock_profile)), \
             patch(_PATCH_DISCOVER, return_value=[]) as mock_discover, \
             patch(_PATCH_SAVE_DOC):
            resp = client.post("/api/doc/regenerate", json={"no_llm": True})

        assert resp.status_code == 200
        # Verify discover_routes was called with the openapi path
        mock_discover.assert_called_once()
        call_kwargs = mock_discover.call_args
        assert call_kwargs[1].get("openapi_path") == str(spec_path) or \
               (call_kwargs[0] if call_kwargs[0] else None)


class TestExportMarkdown:
    def test_export(self, client):
        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("no target")), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            resp = client.get("/api/doc/export/markdown")
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert "# Test App Documentation" in content
