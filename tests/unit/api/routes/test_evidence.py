"""Unit tests for evidence API routes."""
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
    RecommendationRecord,
    RiskRecord,
    ChurnRecord,
)
from qaagent.evidence.run_manager import RunManager


def _seed_run(runs_dir: Path, repo: Path) -> str:
    """Create a run with full evidence data for testing."""
    manager = RunManager(base_dir=runs_dir)
    repo.mkdir(parents=True, exist_ok=True)
    handle = manager.create_run("test-repo", repo)
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)

    writer.write_records(
        "quality",
        [
            FindingRecord(
                evidence_id=id_gen.next_id("fnd"),
                tool="flake8",
                severity="high",
                code="E302",
                message="Expected blank lines",
                file="src/main.py",
                line=10,
                column=1,
            ).to_dict()
        ],
    )

    writer.write_records(
        "coverage",
        [
            CoverageRecord(
                coverage_id=id_gen.next_id("cov"),
                type="line",
                component="src/main.py",
                value=0.75,
                total_statements=100,
                covered_statements=75,
                sources=["coverage.xml"],
            ).to_dict()
        ],
    )

    writer.write_records(
        "churn",
        [
            ChurnRecord(
                evidence_id=id_gen.next_id("chn"),
                path="src/main.py",
                window="90d",
                commits=10,
                lines_added=200,
                lines_deleted=50,
                contributors=3,
            ).to_dict()
        ],
    )

    writer.write_records(
        "risks",
        [
            RiskRecord(
                risk_id=id_gen.next_id("rsk"),
                component="src/main.py",
                score=65.0,
                band="P1",
                confidence=0.8,
                severity="high",
                title="High risk component",
                description="Needs tests",
            ).to_dict()
        ],
    )

    writer.write_records(
        "recommendations",
        [
            RecommendationRecord(
                recommendation_id=id_gen.next_id("rec"),
                component="src/main.py",
                priority="high",
                summary="Add unit tests",
                details="Component has no test coverage",
            ).to_dict()
        ],
    )

    return handle.run_id


@pytest.fixture()
def seeded_app(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    repo = tmp_path / "repo"
    monkeypatch.setenv("QAAGENT_RUNS_DIR", str(runs_dir))
    run_id = _seed_run(runs_dir, repo)
    app = create_app()
    client = TestClient(app)
    yield client, run_id


class TestGetFindings:
    def test_returns_findings(self, seeded_app):
        client, run_id = seeded_app
        resp = client.get(f"/api/runs/{run_id}/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["findings"]) == 1
        assert data["findings"][0]["tool"] == "flake8"
        assert data["findings"][0]["severity"] == "high"

    def test_not_found(self, seeded_app):
        client, _ = seeded_app
        resp = client.get("/api/runs/nonexistent/findings")
        assert resp.status_code == 404


class TestGetCoverage:
    def test_returns_coverage(self, seeded_app):
        client, run_id = seeded_app
        resp = client.get(f"/api/runs/{run_id}/coverage")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["coverage"]) == 1
        assert data["coverage"][0]["value"] == 0.75
        assert data["coverage"][0]["component"] == "src/main.py"

    def test_not_found(self, seeded_app):
        client, _ = seeded_app
        resp = client.get("/api/runs/nonexistent/coverage")
        assert resp.status_code == 404


class TestGetChurn:
    def test_returns_churn(self, seeded_app):
        client, run_id = seeded_app
        resp = client.get(f"/api/runs/{run_id}/churn")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["churn"]) == 1
        assert data["churn"][0]["commits"] == 10
        assert data["churn"][0]["path"] == "src/main.py"

    def test_not_found(self, seeded_app):
        client, _ = seeded_app
        resp = client.get("/api/runs/nonexistent/churn")
        assert resp.status_code == 404


class TestGetRisks:
    def test_returns_risks(self, seeded_app):
        client, run_id = seeded_app
        resp = client.get(f"/api/runs/{run_id}/risks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["risks"]) == 1
        assert data["risks"][0]["band"] == "P1"
        assert data["risks"][0]["score"] == 65.0

    def test_not_found(self, seeded_app):
        client, _ = seeded_app
        resp = client.get("/api/runs/nonexistent/risks")
        assert resp.status_code == 404


class TestGetRecommendations:
    def test_returns_recommendations(self, seeded_app):
        client, run_id = seeded_app
        resp = client.get(f"/api/runs/{run_id}/recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["priority"] == "high"
        assert data["recommendations"][0]["summary"] == "Add unit tests"

    def test_not_found(self, seeded_app):
        client, _ = seeded_app
        resp = client.get("/api/runs/nonexistent/recommendations")
        assert resp.status_code == 404


class TestGetCujCoverage:
    def test_empty_config_returns_empty_journeys(self, seeded_app, monkeypatch):
        client, run_id = seeded_app
        # Point to nonexistent file — CUJConfig.load returns empty config
        monkeypatch.setenv("QAAGENT_CUJ_CONFIG", "/nonexistent/cuj.yaml")
        resp = client.get(f"/api/runs/{run_id}/cuj")
        assert resp.status_code == 200
        assert resp.json()["journeys"] == []

    def test_with_cuj_config(self, seeded_app, tmp_path, monkeypatch):
        client, run_id = seeded_app
        cuj_file = tmp_path / "cuj.yaml"
        cuj_file.write_text(
            "product: test\n"
            "journeys:\n"
            "  - id: j1\n"
            "    name: Login Flow\n"
            "    components:\n"
            "      - src/main.py\n"
            "coverage_targets:\n"
            "  j1: 0.8\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("QAAGENT_CUJ_CONFIG", str(cuj_file))
        resp = client.get(f"/api/runs/{run_id}/cuj")
        assert resp.status_code == 200
        journeys = resp.json()["journeys"]
        assert len(journeys) == 1
        assert journeys[0]["name"] == "Login Flow"
        assert "target" in journeys[0]
        assert "coverage" in journeys[0]
        assert "components" in journeys[0]

    def test_not_found(self, seeded_app, monkeypatch):
        client, _ = seeded_app
        monkeypatch.setenv("QAAGENT_CUJ_CONFIG", "/nonexistent/cuj.yaml")
        resp = client.get("/api/runs/nonexistent/cuj")
        assert resp.status_code == 404
