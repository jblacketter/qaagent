"""Tests for /api/settings and /api/auth/change-password."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from qaagent import db
from qaagent.api.app import create_app



@pytest.fixture()
def client():
    return TestClient(create_app())


# ---- GET /api/settings ----

def test_get_settings_defaults(client):
    """Settings returns expected fields when no data exists."""
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "db_path" in data
    assert data["auth_enabled"] is False
    assert data["username"] is None
    assert data["repos_count"] == 0
    assert isinstance(data["runs_count"], int)


def test_get_settings_with_user(client):
    """Settings reflects auth state when a user exists."""
    db.user_create("admin", "password123")
    # Must authenticate — middleware protects /api/settings when users exist
    client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    resp = client.get("/api/settings")
    data = resp.json()
    assert data["auth_enabled"] is True
    assert data["username"] == "admin"


def test_get_settings_with_repos(client):
    """Settings shows repo count."""
    db.repo_upsert("test-repo", "Test Repo", "/tmp/test", "local")
    resp = client.get("/api/settings")
    data = resp.json()
    assert data["repos_count"] == 1


# ---- POST /api/settings/clear-database ----

def test_clear_database(client):
    """Clear database removes repos and agent configs."""
    db.repo_upsert("test-repo", "Test Repo", "/tmp/test", "local")
    db.agent_config_save("test-repo", "anthropic", "claude-sonnet-4-5-20250929", "sk-test")
    db.agent_usage_add("test-repo", prompt_tokens=100)

    resp = client.post("/api/settings/clear-database")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"

    # Verify data is gone
    assert db.repo_list() == []
    assert db.agent_config_get("test-repo") is None
    usage = db.agent_usage_get("test-repo")
    assert usage["requests"] == 0


def test_clear_database_with_branch_data(client):
    """Clear database succeeds even when branch data exists (regression)."""
    db.repo_upsert("test-repo", "Test Repo", "/tmp/test", "local")
    conn = db.get_db()
    conn.execute(
        "INSERT INTO branches (repo_id, branch_name, stage) VALUES ('test-repo', 'feature/X', 'active')"
    )
    conn.commit()

    resp = client.post("/api/settings/clear-database")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"
    assert db.repo_list() == []
    assert conn.execute("SELECT COUNT(*) as c FROM branches").fetchone()["c"] == 0


# ---- POST /api/auth/change-password ----

def test_change_password_success(client):
    """Changing password with correct old password succeeds."""
    db.user_create("admin", "oldpass12")
    # Login first to get a session
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "oldpass12"})
    assert login_resp.status_code == 200

    resp = client.post(
        "/api/auth/change-password",
        json={"old_password": "oldpass12", "new_password": "newpass12"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "password_changed"

    # Verify new password works
    assert db.user_verify("admin", "newpass12") is not None
    # Verify old password no longer works
    assert db.user_verify("admin", "oldpass12") is None


def test_change_password_wrong_old(client):
    """Changing password with wrong old password fails."""
    db.user_create("admin", "oldpass12")
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "oldpass12"})
    assert login_resp.status_code == 200

    resp = client.post(
        "/api/auth/change-password",
        json={"old_password": "wrongpass", "new_password": "newpass12"},
    )
    assert resp.status_code == 401


def test_change_password_too_short(client):
    """Changing password to one shorter than 8 chars fails."""
    db.user_create("admin", "oldpass12")
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "oldpass12"})
    assert login_resp.status_code == 200

    resp = client.post(
        "/api/auth/change-password",
        json={"old_password": "oldpass12", "new_password": "short"},
    )
    assert resp.status_code == 400


def test_change_password_unauthenticated(client):
    """Change password without a session fails with 401."""
    resp = client.post(
        "/api/auth/change-password",
        json={"old_password": "whatever", "new_password": "whatever1"},
    )
    assert resp.status_code == 401


# ---- clear-database auth guard (regression) ----

def test_clear_database_unauthenticated_rejected(client):
    """clear-database rejects unauthenticated requests when auth is enabled."""
    db.user_create("admin", "password123")
    db.repo_upsert("test-repo", "Test Repo", "/tmp/test", "local")

    # No login — should be rejected
    resp = client.post("/api/settings/clear-database")
    assert resp.status_code == 401

    # Data should still be there
    assert len(db.repo_list()) == 1


def test_clear_database_authenticated_succeeds(client):
    """clear-database works when authenticated."""
    db.user_create("admin", "password123")
    db.repo_upsert("test-repo", "Test Repo", "/tmp/test", "local")

    # Login first
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    assert login_resp.status_code == 200

    resp = client.post("/api/settings/clear-database")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"
    assert db.repo_list() == []
