"""Unit tests for authentication (auth routes + middleware)."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from qaagent import db
from qaagent.api.routes.auth import reset_rate_limits


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    db.reset_connection()
    db.set_db_path(str(tmp_path / "test.db"))
    reset_rate_limits()
    yield
    db.reset_connection()


@pytest.fixture()
def client():
    """TestClient that exercises the web_ui app (with AuthMiddleware)."""
    from qaagent.web_ui import app
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Setup flow
# ---------------------------------------------------------------------------

class TestSetup:
    def test_status_requires_setup_when_no_users(self, client):
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["setup_required"] is True
        assert data["authenticated"] is False

    def test_setup_creates_admin(self, client):
        resp = client.post("/api/auth/setup", json={
            "username": "admin",
            "password": "securepass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["username"] == "admin"
        # Session cookie should be set
        assert "qaagent_session" in resp.cookies

    def test_setup_rejects_second_admin(self, client):
        client.post("/api/auth/setup", json={
            "username": "admin",
            "password": "securepass123",
        })
        resp = client.post("/api/auth/setup", json={
            "username": "admin2",
            "password": "anotherpass1",
        })
        assert resp.status_code == 403

    def test_setup_requires_min_password(self, client):
        resp = client.post("/api/auth/setup", json={
            "username": "admin",
            "password": "short",
        })
        assert resp.status_code == 400
        assert "8 characters" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

class TestLoginLogout:
    def _setup_admin(self, client):
        client.post("/api/auth/setup", json={
            "username": "admin",
            "password": "securepass123",
        })

    def test_login_success(self, client):
        self._setup_admin(client)
        resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "securepass123",
        })
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is True

    def test_login_wrong_password(self, client):
        self._setup_admin(client)
        resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        self._setup_admin(client)
        resp = client.post("/api/auth/login", json={
            "username": "nobody",
            "password": "whatever1",
        })
        assert resp.status_code == 401

    def test_logout(self, client):
        self._setup_admin(client)
        # Login
        login_resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "securepass123",
        })
        # Logout
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged_out"

        # Status should show unauthenticated
        status_resp = client.get("/api/auth/status")
        assert status_resp.json()["authenticated"] is False


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    def _setup_and_login(self, client):
        client.post("/api/auth/setup", json={
            "username": "admin",
            "password": "securepass123",
        })
        return client.post("/api/auth/login", json={
            "username": "admin",
            "password": "securepass123",
        })

    def test_no_users_allows_all(self, client):
        """When no admin exists, middleware should let everything through."""
        resp = client.get("/api/repositories")
        assert resp.status_code == 200

    def test_unauthenticated_api_returns_401(self, client):
        """After admin setup, unauthenticated API calls get 401."""
        db.user_create("admin", "securepass123")
        # Create a fresh client without any cookies
        from qaagent.web_ui import app
        clean_client = TestClient(app, raise_server_exceptions=False)
        resp = clean_client.get("/api/repositories")
        assert resp.status_code == 401

    def test_authenticated_api_works(self, client):
        self._setup_and_login(client)
        resp = client.get("/api/repositories")
        assert resp.status_code == 200

    def test_auth_endpoints_always_accessible(self, client):
        """Auth endpoints should work even without a session."""
        db.user_create("admin", "securepass123")
        from qaagent.web_ui import app
        clean_client = TestClient(app, raise_server_exceptions=False)
        resp = clean_client.get("/api/auth/status")
        assert resp.status_code == 200

    def test_upgrade_websocket_header_does_not_bypass_auth(self, client):
        """Regression: Upgrade: websocket header on API paths must NOT bypass auth."""
        db.user_create("admin", "securepass123")
        from qaagent.web_ui import app
        clean_client = TestClient(app, raise_server_exceptions=False)
        resp = clean_client.get(
            "/api/repositories",
            headers={"Upgrade": "websocket"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_lockout_after_max_attempts(self, client):
        db.user_create("admin", "securepass123")
        # 5 failed attempts
        for _ in range(5):
            client.post("/api/auth/login", json={
                "username": "admin",
                "password": "wrong",
            })
        # 6th should be rate limited
        resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrong",
        })
        assert resp.status_code == 429
        assert "Too many" in resp.json()["detail"]

    def test_successful_login_not_affected_by_others_failures(self, client):
        """After failed attempts, correct password still works (within limit)."""
        db.user_create("admin", "securepass123")
        # 3 failed attempts (under limit)
        for _ in range(3):
            client.post("/api/auth/login", json={
                "username": "admin",
                "password": "wrong",
            })
        # Correct login should still work
        resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "securepass123",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Session expiry
# ---------------------------------------------------------------------------

class TestSessionExpiry:
    def test_expired_session_returns_401(self, client):
        db.user_create("admin", "securepass123")
        login_resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "securepass123",
        })
        assert login_resp.status_code == 200

        # Force session expiry
        conn = db.get_db()
        conn.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00'")
        conn.commit()

        resp = client.get("/api/repositories")
        assert resp.status_code == 401
