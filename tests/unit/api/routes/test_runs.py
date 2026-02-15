"""Unit tests for runs API routes."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from qaagent.api.app import create_app
from qaagent.evidence import (
    CoverageRecord,
    EvidenceIDGenerator,
    EvidenceWriter,
    FindingRecord,
    RiskRecord,
)
from qaagent.evidence.run_manager import RunManager


def _seed_runs(runs_dir: Path, repo: Path, count: int = 1) -> list[str]:
    """Create multiple runs with evidence data."""
    manager = RunManager(base_dir=runs_dir)
    repo.mkdir(parents=True, exist_ok=True)
    run_ids = []

    for i in range(count):
        handle = manager.create_run(f"repo-{i}", repo)
        writer = EvidenceWriter(handle)
        id_gen = EvidenceIDGenerator(handle.run_id)

        writer.write_records(
            "coverage",
            [
                CoverageRecord(
                    coverage_id=id_gen.next_id("cov"),
                    type="line",
                    component="src/main.py",
                    value=0.5 + i * 0.1,
                    total_statements=100,
                    covered_statements=50 + i * 10,
                    sources=["coverage.xml"],
                ).to_dict()
            ],
        )

        writer.write_records(
            "risks",
            [
                RiskRecord(
                    risk_id=id_gen.next_id("rsk"),
                    component="src/main.py",
                    score=50.0 + i * 10,
                    band="P1" if i == 0 else "P2",
                    confidence=0.8,
                    severity="high" if i == 0 else "medium",
                    title=f"Risk {i}",
                    description="Test risk",
                ).to_dict()
            ],
        )

        run_ids.append(handle.run_id)

    return run_ids


@pytest.fixture()
def app_with_runs(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    repo = tmp_path / "repo"
    monkeypatch.setenv("QAAGENT_RUNS_DIR", str(runs_dir))
    run_ids = _seed_runs(runs_dir, repo, count=3)
    app = create_app()
    client = TestClient(app)
    yield client, run_ids


class TestListRuns:
    def test_returns_all_runs(self, app_with_runs):
        client, run_ids = app_with_runs
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["runs"]) == 3

    def test_pagination_limit(self, app_with_runs):
        client, run_ids = app_with_runs
        resp = client.get("/api/runs?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 2
        assert data["total"] == 3

    def test_pagination_offset(self, app_with_runs):
        client, run_ids = app_with_runs
        resp = client.get("/api/runs?limit=2&offset=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 1

    def test_run_structure(self, app_with_runs):
        client, run_ids = app_with_runs
        resp = client.get("/api/runs?limit=1")
        run_entry = resp.json()["runs"][0]
        assert "run_id" in run_entry
        assert "created_at" in run_entry
        assert "target" in run_entry
        assert "counts" in run_entry


class TestGetRun:
    def test_returns_manifest(self, app_with_runs):
        client, run_ids = app_with_runs
        resp = client.get(f"/api/runs/{run_ids[0]}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_ids[0]

    def test_not_found(self, app_with_runs):
        client, _ = app_with_runs
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code == 404


class TestGetRunTrends:
    def test_returns_trend_data(self, app_with_runs):
        client, run_ids = app_with_runs
        resp = client.get("/api/runs/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert "trend" in data
        assert data["total"] == 3
        # Points are in chronological order
        points = data["trend"]
        assert len(points) == 3
        for point in points:
            assert "run_id" in point
            assert "average_coverage" in point
            assert "risk_counts" in point

    def test_trend_limit(self, app_with_runs):
        client, _ = app_with_runs
        resp = client.get("/api/runs/trends?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trend"]) == 2
