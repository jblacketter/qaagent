"""Integration test: create repo → analyze → GET /api/doc?repo_id=X (Phase 17)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from qaagent.api.routes.repositories import repositories


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Point SQLite at a temp file so tests don't touch the real DB."""
    from qaagent import db
    db.reset_connection()
    db.set_db_path(str(tmp_path / "test.db"))
    yield
    db.reset_connection()


@pytest.fixture(autouse=True)
def _isolate_qaagent_home(tmp_path, monkeypatch):
    """Redirect QAAGENT_HOME to tmp_path so TargetManager doesn't write to user-global config."""
    qaagent_home = tmp_path / ".qaagent-home"
    qaagent_home.mkdir()
    monkeypatch.setenv("QAAGENT_HOME", str(qaagent_home))


@pytest.fixture()
def client():
    from qaagent.web_ui import app
    return TestClient(app)


def test_analyze_generates_doc_accessible_by_repo_id(client: TestClient, tmp_path):
    """End-to-end: create local repo → analyze → doc endpoint returns repo-scoped docs."""
    # Create a minimal source file so route discovery has something to scan
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.ts").write_text("// placeholder", encoding="utf-8")

    # Step 1: Create repository
    response = client.post("/api/repositories", json={
        "name": "integration-test-repo",
        "path": str(tmp_path),
        "repo_type": "local",
        "analysis_options": {"testCoverage": False, "security": False, "performance": False, "codeQuality": False, "testCases": False},
    })
    assert response.status_code == 200, response.text
    repo = response.json()
    repo_id = repo["id"]

    # Step 2: Trigger analysis (route discovery + doc generation)
    response = client.post(f"/api/repositories/{repo_id}/analyze", json={"force": False})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"

    # Step 3: Verify doc is accessible via repo_id
    response = client.get("/api/doc", params={"repo_id": repo_id})
    assert response.status_code == 200, f"Doc not found after analysis: {response.text}"
    doc = response.json()
    assert doc["app_name"] == "integration-test-repo"
    # Doc should have been generated (may have 0 routes for a placeholder project, but features list exists)
    assert "features" in doc
    assert "integrations" in doc
