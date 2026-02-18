"""Unit tests for repositories API routes."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from qaagent.api.app import create_app
from qaagent.api.routes.repositories import repositories


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Point SQLite at a temp file so tests don't touch the real DB."""
    from qaagent import db
    db.reset_connection()
    db.set_db_path(str(tmp_path / "test.db"))
    yield
    db.reset_connection()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("QAAGENT_RUNS_DIR", str(tmp_path / "runs"))
    (tmp_path / "runs").mkdir()
    app = create_app()
    return TestClient(app)


def _create_repo(client, tmp_path, name="my-app", repo_type="local"):
    """Helper to create a repository via the API."""
    project = tmp_path / name
    project.mkdir(exist_ok=True)
    return client.post("/api/repositories", json={
        "name": name,
        "path": str(project),
        "repo_type": repo_type,
        "analysis_options": {"testCoverage": True, "codeQuality": True},
    })


class TestListRepositories:
    def test_empty(self, client):
        resp = client.get("/api/repositories")
        assert resp.status_code == 200
        assert resp.json()["repositories"] == []

    def test_with_repos(self, client, tmp_path):
        _create_repo(client, tmp_path, "app-a")
        _create_repo(client, tmp_path, "app-b")
        resp = client.get("/api/repositories")
        assert resp.status_code == 200
        assert len(resp.json()["repositories"]) == 2


class TestCreateRepository:
    def test_create_local(self, client, tmp_path):
        resp = _create_repo(client, tmp_path)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my-app"
        assert data["repo_type"] == "local"
        assert data["status"] == "ready"

    def test_duplicate_name(self, client, tmp_path):
        _create_repo(client, tmp_path, "dup")
        resp = _create_repo(client, tmp_path, "dup")
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_local_path_not_exists(self, client, tmp_path):
        resp = client.post("/api/repositories", json={
            "name": "bad-path",
            "path": str(tmp_path / "nonexistent"),
            "repo_type": "local",
            "analysis_options": {},
        })
        assert resp.status_code == 400
        assert "does not exist" in resp.json()["detail"]

    def test_local_path_not_dir(self, client, tmp_path):
        file_path = tmp_path / "afile.txt"
        file_path.write_text("hi")
        resp = client.post("/api/repositories", json={
            "name": "file-path",
            "path": str(file_path),
            "repo_type": "local",
            "analysis_options": {},
        })
        assert resp.status_code == 400
        assert "not a directory" in resp.json()["detail"]

    def test_create_github(self, client, tmp_path):
        resp = client.post("/api/repositories", json={
            "name": "gh-repo",
            "path": "https://github.com/user/repo",
            "repo_type": "github",
            "analysis_options": {"security": True},
        })
        assert resp.status_code == 200
        assert resp.json()["repo_type"] == "github"


class TestGetRepository:
    def test_found(self, client, tmp_path):
        _create_repo(client, tmp_path, "myrepo")
        resp = client.get("/api/repositories/myrepo")
        assert resp.status_code == 200
        assert resp.json()["name"] == "myrepo"

    def test_not_found(self, client):
        resp = client.get("/api/repositories/nonexistent")
        assert resp.status_code == 404


class TestDeleteRepository:
    def test_delete_success(self, client, tmp_path):
        _create_repo(client, tmp_path, "to-delete")
        resp = client.delete("/api/repositories/to-delete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        # Verify it's gone
        assert client.get("/api/repositories/to-delete").status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/repositories/nonexistent")
        assert resp.status_code == 404


class TestAnalyzeRepository:
    def test_success(self, client, tmp_path):
        _create_repo(client, tmp_path, "analyze-me")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch("qaagent.api.routes.repositories.subprocess.run", return_value=mock_result):
            resp = client.post("/api/repositories/analyze-me/analyze", json={"force": False})
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_not_found(self, client):
        resp = client.post("/api/repositories/nonexistent/analyze", json={"force": False})
        assert resp.status_code == 404

    def test_analysis_failure(self, client, tmp_path):
        _create_repo(client, tmp_path, "fail-repo")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Analysis error"
        with patch("qaagent.api.routes.repositories.subprocess.run", return_value=mock_result):
            resp = client.post("/api/repositories/fail-repo/analyze", json={"force": False})
        assert resp.status_code == 500


class TestGetRepositoryStatus:
    def test_status(self, client, tmp_path):
        _create_repo(client, tmp_path, "status-repo")
        resp = client.get("/api/repositories/status-repo/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["last_scan"] == "never"

    def test_not_found(self, client):
        resp = client.get("/api/repositories/nonexistent/status")
        assert resp.status_code == 404


class TestGetRepositoryRuns:
    def test_returns_runs(self, client, tmp_path, monkeypatch):
        _create_repo(client, tmp_path, "runs-repo")
        # No actual runs seeded, but the endpoint should still work
        resp = client.get("/api/repositories/runs-repo/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["repo_id"] == "runs-repo"
        assert isinstance(data["runs"], list)

    def test_not_found(self, client):
        resp = client.get("/api/repositories/nonexistent/runs")
        assert resp.status_code == 404
