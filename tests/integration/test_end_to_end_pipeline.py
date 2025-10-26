from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from qaagent.api.app import create_app
from qaagent.commands.analyze import ensure_risks, ensure_recommendations
from qaagent.evidence import (
    EvidenceWriter,
    EvidenceIDGenerator,
    FindingRecord,
    CoverageRecord,
    ChurnRecord,
)
from qaagent.evidence.run_manager import RunManager


def _seed_evidence(handle):
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
                message="expected blank lines",
                file="src/auth/session.py",
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
                component="src/auth/session.py",
                value=0.3,
                total_statements=10,
                covered_statements=3,
                sources=["coverage.xml"],
            ).to_dict()
        ],
    )
    writer.write_records(
        "churn",
        [
            ChurnRecord(
                evidence_id=id_gen.next_id("chn"),
                path="src/auth/session.py",
                window="90d",
                commits=12,
                lines_added=120,
                lines_deleted=40,
                contributors=4,
            ).to_dict()
        ],
    )


def test_end_to_end_pipeline(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    repo = tmp_path / "repo"
    repo.mkdir()

    manager = RunManager(base_dir=runs_dir)
    handle = manager.create_run("repo", repo)
    _seed_evidence(handle)

    ensure_risks(handle.run_dir.as_posix(), runs_dir, Path("handoff/risk_config.yaml"))
    ensure_recommendations(
        handle.run_dir.as_posix(),
        runs_dir,
        Path("handoff/risk_config.yaml"),
        Path("handoff/cuj.yaml"),
    )

    os.environ["QAAGENT_RUNS_DIR"] = str(runs_dir)
    client = TestClient(create_app())

    assert client.get("/api/runs").status_code == 200
    run_id = handle.run_id
    assert client.get(f"/api/runs/{run_id}").status_code == 200
    assert client.get(f"/api/runs/{run_id}/risks").json()["risks"]
    assert client.get(f"/api/runs/{run_id}/recommendations").json()["recommendations"]
