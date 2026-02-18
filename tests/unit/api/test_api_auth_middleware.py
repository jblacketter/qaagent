"""Tests for AuthMiddleware on the standalone API app."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from qaagent import db
from qaagent.api.app import create_app



@pytest.fixture()
def client():
    return TestClient(create_app())


def _login(client: TestClient, username: str = "admin", password: str = "password123"):
    """Create a user, login, and return the client (cookies are stored)."""
    db.user_create(username, password)
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return client


# ---- Setup mode (no users) — everything allowed ----

def test_setup_mode_allows_protected_endpoints(client):
    """When no users exist, all endpoints are accessible."""
    resp = client.get("/api/settings")
    assert resp.status_code == 200


def test_setup_mode_allows_repositories(client):
    """When no users exist, repositories endpoint is accessible."""
    resp = client.get("/api/repositories")
    assert resp.status_code == 200


# ---- Exempt paths always allowed ----

def test_auth_status_no_auth_required(client):
    """/api/auth/status is exempt even when users exist."""
    db.user_create("admin", "password123")
    resp = client.get("/api/auth/status")
    assert resp.status_code == 200


def test_health_no_auth_required(client):
    """/health is exempt even when users exist."""
    db.user_create("admin", "password123")
    resp = client.get("/health")
    assert resp.status_code == 200


# ---- Unauthenticated requests rejected when users exist ----

def test_unauthenticated_get_settings_rejected(client):
    """GET /api/settings returns 401 when auth is enabled."""
    db.user_create("admin", "password123")
    resp = client.get("/api/settings")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Authentication required"


def test_unauthenticated_get_repositories_rejected(client):
    """GET /api/repositories returns 401 when auth is enabled."""
    db.user_create("admin", "password123")
    resp = client.get("/api/repositories")
    assert resp.status_code == 401


def test_unauthenticated_delete_repository_rejected(client):
    """DELETE /api/repositories/x returns 401 when auth is enabled."""
    db.user_create("admin", "password123")
    resp = client.delete("/api/repositories/test-repo")
    assert resp.status_code == 401


def test_unauthenticated_clear_database_rejected(client):
    """POST /api/settings/clear-database returns 401 when auth is enabled."""
    db.user_create("admin", "password123")
    resp = client.post("/api/settings/clear-database")
    assert resp.status_code == 401


def test_unauthenticated_non_api_path_returns_401(client):
    """Standalone API returns 401 (not redirect) for non-API paths."""
    db.user_create("admin", "password123")
    resp = client.get("/docs", follow_redirects=False)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Authentication required"


# ---- Authenticated requests succeed ----

def test_authenticated_get_settings(client):
    """GET /api/settings succeeds with valid session."""
    _login(client)
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    assert "version" in resp.json()


def test_authenticated_get_repositories(client):
    """GET /api/repositories succeeds with valid session."""
    _login(client)
    resp = client.get("/api/repositories")
    assert resp.status_code == 200


def test_authenticated_clear_database(client):
    """POST /api/settings/clear-database succeeds with valid session."""
    _login(client)
    db.repo_upsert("test-repo", "Test Repo", "/tmp/test", "local")
    resp = client.post("/api/settings/clear-database")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"
    assert db.repo_list() == []
