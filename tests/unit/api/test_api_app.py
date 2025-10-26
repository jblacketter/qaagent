from __future__ import annotations

import os
from pathlib import Path

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
    manager = RunManager(base_dir=runs_dir)
    repo.mkdir(parents=True, exist_ok=True)
    handle = manager.create_run("repo", repo)
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
                file="src/auth/login.py",
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
                component="src/auth/login.py",
                value=0.5,
                total_statements=10,
                covered_statements=5,
                sources=["coverage.xml"],
            ).to_dict()
        ],
    )

    writer.write_records(
        "churn",
        [
            ChurnRecord(
                evidence_id=id_gen.next_id("chn"),
                path="src/auth/login.py",
                window="90d",
                commits=5,
                lines_added=50,
                lines_deleted=10,
                contributors=2,
            ).to_dict()
        ],
    )

    writer.write_records(
        "risks",
        [
            RiskRecord(
                risk_id=id_gen.next_id("rsk"),
                component="src/auth/login.py",
                score=75.0,
                band="P1",
                confidence=0.7,
                severity="high",
                title="Auth risk",
                description="",
            ).to_dict()
        ],
    )

    writer.write_records(
        "recommendations",
        [
            RecommendationRecord(
                recommendation_id=id_gen.next_id("rec"),
                component="src/auth/login.py",
                priority="high",
                summary="Add tests",
                details="Increase coverage",
            ).to_dict()
        ],
    )

    return handle.run_id


def test_api_routes(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    repo = tmp_path / "repo"
    os.environ["QAAGENT_RUNS_DIR"] = str(runs_dir)
    run_id = _seed_run(runs_dir, repo)

    app = create_app()
    client = TestClient(app)

    assert client.get("/health").status_code == 200

    runs_response = client.get("/api/runs")
    assert runs_response.status_code == 200
    assert runs_response.json()["runs"]

    run_detail = client.get(f"/api/runs/{run_id}")
    assert run_detail.status_code == 200
    assert run_detail.json()["run_id"] == run_id

    assert client.get(f"/api/runs/{run_id}/findings").json()["findings"]
    assert client.get(f"/api/runs/{run_id}/coverage").json()["coverage"]
    assert client.get(f"/api/runs/{run_id}/churn").json()["churn"]
    assert client.get(f"/api/runs/{run_id}/risks").json()["risks"]
    assert client.get(f"/api/runs/{run_id}/recommendations").json()["recommendations"]
