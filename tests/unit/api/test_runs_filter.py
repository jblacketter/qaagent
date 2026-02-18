"""Tests for repo_id filtering on /api/runs and /api/runs/trends."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from qaagent.api.app import create_app


@pytest.fixture()
def client_with_runs(tmp_path, monkeypatch):
    """Create a test client with two fake runs for different targets."""
    runs_dir = tmp_path / "runs"

    # Run A — target "alpha"
    run_a = runs_dir / "20260101_120000Z"
    (run_a / "evidence").mkdir(parents=True)
    (run_a / "artifacts").mkdir(parents=True)
    manifest_a = {
        "run_id": "20260101_120000Z",
        "created_at": "2026-01-01T12:00:00Z",
        "target": {"name": "Alpha", "path": "/tmp/alpha", "git": {}},
        "tools": {},
        "counts": {"findings": 0, "risks": 0, "tests": 0, "coverage_components": 0},
        "evidence_files": {},
        "diagnostics": [],
    }
    (run_a / "manifest.json").write_text(json.dumps(manifest_a), encoding="utf-8")

    # Run B — target "beta"
    run_b = runs_dir / "20260102_120000Z"
    (run_b / "evidence").mkdir(parents=True)
    (run_b / "artifacts").mkdir(parents=True)
    manifest_b = {
        "run_id": "20260102_120000Z",
        "created_at": "2026-01-02T12:00:00Z",
        "target": {"name": "Beta", "path": "/tmp/beta", "git": {}},
        "tools": {},
        "counts": {"findings": 0, "risks": 0, "tests": 0, "coverage_components": 0},
        "evidence_files": {},
        "diagnostics": [],
    }
    (run_b / "manifest.json").write_text(json.dumps(manifest_b), encoding="utf-8")

    # Point RunManager at our temp runs dir via env var
    monkeypatch.setenv("QAAGENT_RUNS_DIR", str(runs_dir))

    app = create_app()
    yield TestClient(app)


def test_list_runs_no_filter(client_with_runs):
    """Without repo_id, all runs are returned."""
    resp = client_with_runs.get("/api/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["runs"]) == 2


def test_list_runs_filter_alpha(client_with_runs):
    """Filter by repo_id=alpha returns only the Alpha run."""
    resp = client_with_runs.get("/api/runs?repo_id=alpha")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["runs"][0]["target"]["name"] == "Alpha"


def test_list_runs_filter_beta(client_with_runs):
    """Filter by repo_id=beta returns only the Beta run."""
    resp = client_with_runs.get("/api/runs?repo_id=beta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["runs"][0]["target"]["name"] == "Beta"


def test_list_runs_filter_nonexistent(client_with_runs):
    """Filter by non-existent repo returns empty list."""
    resp = client_with_runs.get("/api/runs?repo_id=nope")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["runs"] == []


def test_trends_no_filter(client_with_runs):
    """Without repo_id, trends include all runs."""
    resp = client_with_runs.get("/api/runs/trends")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_trends_filter(client_with_runs):
    """With repo_id, trends include only matching runs."""
    resp = client_with_runs.get("/api/runs/trends?repo_id=alpha")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
