"""Contract tests for repo-aware doc API endpoints (Phase 17)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from qaagent.api.routes.repositories import Repository, repositories
from qaagent.doc.generator import save_documentation
from qaagent.doc.models import (
    AppDocumentation,
    JourneyStep,
    UserJourney,
    UserRole,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Point SQLite at a temp file so tests don't touch the real DB."""
    from qaagent import db
    db.reset_connection()
    db.set_db_path(str(tmp_path / "test.db"))
    yield
    db.reset_connection()


@pytest.fixture()
def client():
    """Create a test client for the web_ui app (has all routers mounted)."""
    from qaagent.web_ui import app
    return TestClient(app)


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Repository:
    """Register a sample repo with pre-generated documentation."""
    repo = Repository(
        id="test-repo",
        name="test-repo",
        path=str(tmp_path),
        repo_type="local",
        analysis_options={"testCoverage": True},
    )
    repositories["test-repo"] = repo

    # Generate minimal documentation
    doc = AppDocumentation(
        app_name="test-repo",
        generated_at="2026-01-01T00:00:00",
        content_hash="abc123",
        source_dir=str(tmp_path),
        features=[],
        integrations=[],
        total_routes=5,
    )
    save_documentation(doc, tmp_path)
    return repo


class TestGetDocWithRepoId:
    """GET /api/doc?repo_id=<value> contract tests."""

    def test_valid_repo_id_returns_scoped_doc(self, client: TestClient, sample_repo: Repository):
        """repo_id provided + found → 200 with repo-scoped documentation."""
        response = client.get("/api/doc", params={"repo_id": "test-repo"})
        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == "test-repo"
        assert data["total_routes"] == 5

    def test_invalid_repo_id_returns_404(self, client: TestClient):
        """repo_id provided + not found → 404 (no silent fallback)."""
        response = client.get("/api/doc", params={"repo_id": "nonexistent"})
        assert response.status_code == 404
        assert "nonexistent" in response.json()["detail"]

    def test_no_repo_id_uses_fallback(self, client: TestClient):
        """repo_id omitted → existing fallback behavior (404 if no active profile docs)."""
        # With no active profile and no docs in cwd, should get 404
        with patch("qaagent.api.routes.doc.load_documentation", return_value=None):
            response = client.get("/api/doc")
        assert response.status_code == 404
        assert "No documentation found" in response.json()["detail"]


class TestRegenerateDocWithRepoId:
    """POST /api/doc/regenerate?repo_id=<value> contract tests."""

    def test_regenerate_valid_repo_id(self, client: TestClient, sample_repo: Repository):
        """regenerate with valid repo_id → 200, regenerated doc has correct source_dir."""
        response = client.post(
            "/api/doc/regenerate",
            params={"repo_id": "test-repo"},
            json={"no_llm": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == "test-repo"
        assert data["source_dir"] == sample_repo.path

    def test_regenerate_invalid_repo_id(self, client: TestClient):
        """regenerate with invalid repo_id → 404."""
        response = client.post(
            "/api/doc/regenerate",
            params={"repo_id": "nonexistent"},
            json={"no_llm": True},
        )
        assert response.status_code == 404
        assert "nonexistent" in response.json()["detail"]


class TestPhase19Fields:
    """Contract tests: Phase 19 fields (app_overview, tech_stack, user_roles, user_journeys) in GET /api/doc."""

    @pytest.fixture()
    def repo_with_enhanced_doc(self, tmp_path: Path) -> Repository:
        """Register a repo with Phase 19 enhanced documentation."""
        repo = Repository(
            id="enhanced-repo",
            name="enhanced-repo",
            path=str(tmp_path),
            repo_type="local",
            analysis_options={},
        )
        repositories["enhanced-repo"] = repo

        doc = AppDocumentation(
            app_name="enhanced-repo",
            total_routes=10,
            app_overview="This is a multi-paragraph overview.\n\nIt describes the application.",
            tech_stack=["Python", "FastAPI", "React"],
            user_roles=[
                UserRole(id="user", name="User", description="End user", permissions=["view", "create"]),
                UserRole(id="admin", name="Admin", description="Administrator", permissions=["manage"]),
            ],
            user_journeys=[
                UserJourney(
                    id="j1", name="Login Flow", actor="user", priority="high",
                    steps=[JourneyStep(order=1, action="Log in", expected_outcome="Authenticated")],
                ),
            ],
        )
        save_documentation(doc, tmp_path)
        return repo

    def test_enhanced_doc_has_app_overview(self, client: TestClient, repo_with_enhanced_doc: Repository):
        """GET /api/doc returns app_overview as string."""
        response = client.get("/api/doc", params={"repo_id": "enhanced-repo"})
        assert response.status_code == 200
        data = response.json()
        assert "app_overview" in data
        assert isinstance(data["app_overview"], str)
        assert "multi-paragraph" in data["app_overview"]

    def test_enhanced_doc_has_tech_stack(self, client: TestClient, repo_with_enhanced_doc: Repository):
        """GET /api/doc returns tech_stack as list of strings."""
        response = client.get("/api/doc", params={"repo_id": "enhanced-repo"})
        data = response.json()
        assert "tech_stack" in data
        assert isinstance(data["tech_stack"], list)
        assert data["tech_stack"] == ["Python", "FastAPI", "React"]

    def test_enhanced_doc_has_user_roles(self, client: TestClient, repo_with_enhanced_doc: Repository):
        """GET /api/doc returns user_roles as list with correct shape."""
        response = client.get("/api/doc", params={"repo_id": "enhanced-repo"})
        data = response.json()
        assert "user_roles" in data
        assert isinstance(data["user_roles"], list)
        assert len(data["user_roles"]) == 2
        role = data["user_roles"][0]
        assert "id" in role
        assert "name" in role
        assert "permissions" in role
        assert isinstance(role["permissions"], list)

    def test_enhanced_doc_has_user_journeys(self, client: TestClient, repo_with_enhanced_doc: Repository):
        """GET /api/doc returns user_journeys as list with correct shape."""
        response = client.get("/api/doc", params={"repo_id": "enhanced-repo"})
        data = response.json()
        assert "user_journeys" in data
        assert isinstance(data["user_journeys"], list)
        assert len(data["user_journeys"]) == 1
        journey = data["user_journeys"][0]
        assert journey["name"] == "Login Flow"
        assert journey["priority"] == "high"
        assert "steps" in journey
        assert isinstance(journey["steps"], list)
        assert journey["steps"][0]["action"] == "Log in"
        assert journey["steps"][0]["expected_outcome"] == "Authenticated"

    def test_legacy_doc_has_default_new_fields(self, client: TestClient, sample_repo: Repository):
        """GET /api/doc for a pre-Phase 19 doc returns defaults for new fields."""
        response = client.get("/api/doc", params={"repo_id": "test-repo"})
        assert response.status_code == 200
        data = response.json()
        assert data.get("app_overview", "") == ""
        assert data.get("tech_stack", []) == []
        assert data.get("user_roles", []) == []
        assert data.get("user_journeys", []) == []
