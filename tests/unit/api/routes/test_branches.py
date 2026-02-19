"""Unit tests for branch API endpoints (phase 25d: generate-tests, run-tests, promote)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from qaagent.api.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    return TestClient(app)


# Lazy imports in the endpoint functions require patching at source locations.
_PATCH_STORE = "qaagent.api.routes.branches.store"
_PATCH_DB = "qaagent.branch.store.db"  # underlying db used by store functions
_PATCH_GEN = "qaagent.branch.test_executor.generate_branch_tests"
_PATCH_RUN = "qaagent.branch.test_executor.run_branch_tests"


# ---------------------------------------------------------------------------
# POST /api/branches/{id}/generate-tests
# ---------------------------------------------------------------------------


class TestGenerateTestsEndpoint:
    """Test generate-tests endpoint."""

    def test_branch_not_found_returns_404(self, client):
        with patch(_PATCH_STORE) as mock_store:
            mock_store.branch_get.return_value = None
            resp = client.post("/api/branches/999/generate-tests")
        assert resp.status_code == 404

    def test_repo_not_found_returns_404(self, client):
        card = MagicMock(id=1, repo_id="repo1", branch_name="feat", base_branch="main")
        with patch(_PATCH_STORE) as mock_store:
            mock_store.branch_get.return_value = card
            # db is imported lazily inside the function, need to patch at qaagent.db level
            with patch("qaagent.db.repo_get", return_value=None):
                resp = client.post("/api/branches/1/generate-tests")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/branches/{id}/run-tests
# ---------------------------------------------------------------------------


class TestRunTestsEndpoint:

    def test_branch_not_found(self, client):
        with patch(_PATCH_STORE) as mock_store:
            mock_store.branch_get.return_value = None
            resp = client.post("/api/branches/999/run-tests")
        assert resp.status_code == 404

    def test_no_generated_tests_returns_400(self, client):
        card = MagicMock(id=1)
        with patch(_PATCH_STORE) as mock_store:
            mock_store.branch_get.return_value = card
            with patch(
                "qaagent.branch.test_executor.run_branch_tests",
                side_effect=FileNotFoundError("No generated tests found for branch 1"),
            ):
                resp = client.post("/api/branches/1/run-tests")
        assert resp.status_code == 400
        assert "generated tests" in resp.json()["detail"].lower()

    def test_success_stores_and_returns_run(self, client):
        card = MagicMock(id=1)
        mock_result = MagicMock(
            total=10, passed=9, failed=1, skipped=0,
            suite_type="pytest", run_id="branch-1-20260219",
        )
        with patch(_PATCH_STORE) as mock_store:
            mock_store.branch_get.return_value = card
            with patch(
                "qaagent.branch.test_executor.run_branch_tests",
                return_value=mock_result,
            ):
                resp = client.post("/api/branches/1/run-tests")

        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == 10
        assert data["summary"]["passed"] == 9
        assert data["test_run"]["suite_type"] == "pytest"
        mock_store.test_run_create.assert_called_once()


# ---------------------------------------------------------------------------
# PATCH /api/branches/test-runs/{id}/promote
# ---------------------------------------------------------------------------


class TestPromoteEndpoint:

    def test_not_found(self, client):
        with patch(_PATCH_STORE) as mock_store:
            mock_store.test_run_promote.return_value = False
            resp = client.patch("/api/branches/test-runs/999/promote")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_success(self, client):
        with patch(_PATCH_STORE) as mock_store:
            mock_store.test_run_promote.return_value = True
            resp = client.patch("/api/branches/test-runs/42/promote")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "promoted"
        assert data["id"] == 42
