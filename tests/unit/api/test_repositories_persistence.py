"""Tests that verify repository data persists across simulated restarts."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from qaagent import db
from qaagent.api.app import create_app
from qaagent.api.routes.repositories import repositories, Repository


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Each test gets its own fresh SQLite database."""
    db_file = str(tmp_path / "test.db")
    db.reset_connection()
    db.set_db_path(db_file)
    yield db_file
    db.reset_connection()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("QAAGENT_RUNS_DIR", str(tmp_path / "runs"))
    (tmp_path / "runs").mkdir()
    app = create_app()
    return TestClient(app)


def _create_repo(client, tmp_path, name="my-app"):
    project = tmp_path / name
    project.mkdir(exist_ok=True)
    return client.post("/api/repositories", json={
        "name": name,
        "path": str(project),
        "repo_type": "local",
        "analysis_options": {"testCoverage": True},
    })


class TestPersistenceAcrossRestart:
    def test_repo_survives_reconnection(self, client, tmp_path, isolated_db):
        """Add a repo, reset the connection (simulating restart), verify it's still there."""
        resp = _create_repo(client, tmp_path, "persist-test")
        assert resp.status_code == 200

        # Simulate server restart by resetting connection and re-pointing to same file
        db.reset_connection()
        db.set_db_path(isolated_db)

        # The RepositoryStore reads from SQLite, so the repo should still be there
        assert "persist-test" in repositories
        repo = repositories["persist-test"]
        assert repo.name == "persist-test"
        assert repo.analysis_options == {"testCoverage": True}

    def test_delete_persists(self, client, tmp_path, isolated_db):
        _create_repo(client, tmp_path, "del-test")
        client.delete("/api/repositories/del-test")

        db.reset_connection()
        db.set_db_path(isolated_db)

        assert "del-test" not in repositories

    def test_status_update_persists(self, tmp_path, isolated_db):
        """Directly test that status changes written via _persist survive reconnection."""
        repo = Repository(
            id="s-test",
            name="s-test",
            path=str(tmp_path),
            repo_type="local",
            analysis_options={},
        )
        repositories["s-test"] = repo

        # Mutate and persist
        repo.status = "analyzing"
        repo.run_count = 5
        repo.last_scan = "2025-06-01T00:00:00"
        repositories["s-test"] = repo

        db.reset_connection()
        db.set_db_path(isolated_db)

        loaded = repositories["s-test"]
        assert loaded.status == "analyzing"
        assert loaded.run_count == 5
        assert loaded.last_scan == "2025-06-01T00:00:00"


class TestRepositoryStoreInterface:
    """Verify the dict-like interface of RepositoryStore."""

    def test_contains(self, tmp_path):
        assert "x" not in repositories
        db.repo_upsert("x", "X", str(tmp_path))
        assert "x" in repositories

    def test_getitem_missing_raises(self):
        with pytest.raises(KeyError):
            _ = repositories["missing"]

    def test_delitem_missing_raises(self):
        with pytest.raises(KeyError):
            del repositories["missing"]

    def test_get_default(self):
        assert repositories.get("nope") is None
        assert repositories.get("nope", "fallback") == "fallback"

    def test_values(self, tmp_path):
        db.repo_upsert("a", "A", str(tmp_path))
        db.repo_upsert("b", "B", str(tmp_path))
        vals = repositories.values()
        assert len(vals) == 2
        names = {v.name for v in vals}
        assert names == {"A", "B"}

    def test_clear(self, tmp_path):
        db.repo_upsert("a", "A", str(tmp_path))
        repositories.clear()
        assert db.repo_list() == []
