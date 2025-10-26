from __future__ import annotations

from pathlib import Path

import pytest

from qaagent.analyzers.evidence_reader import EvidenceReader
from qaagent.analyzers.risk_aggregator import RiskAggregator
from qaagent.analyzers.risk_config import RiskConfig, RiskWeights
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator, FindingRecord
from qaagent.evidence.run_manager import RunManager


@pytest.fixture
def run_handle(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("repo", repo)
    return handle


def _seed_evidence(handle, findings, coverage, churn):
    writer = EvidenceWriter(handle)
    writer.write_records("quality", [f.to_dict() for f in findings])
    writer.write_records("coverage", coverage)
    writer.write_records("churn", churn)


def test_risk_aggregator_basic(run_handle):
    id_gen = EvidenceIDGenerator(run_handle.run_id)
    findings = [
        FindingRecord(
            evidence_id=id_gen.next_id("fnd"),
            tool="flake8",
            severity="high",
            code="E302",
            message="Expected blank lines",
            file="src/auth/login.py",
            line=10,
            column=1,
        )
    ]
    coverage = [
        {
            "coverage_id": id_gen.next_id("cov"),
            "type": "line",
            "component": "src/auth/login.py",
            "value": 0.4,
        },
        {
            "coverage_id": id_gen.next_id("cov"),
            "type": "line",
            "component": "src/other.py",
            "value": 0.9,
        },
    ]
    churn = [
        {
            "evidence_id": id_gen.next_id("chn"),
            "path": "src/auth/login.py",
            "window": "90d",
            "commits": 10,
            "lines_added": 200,
            "lines_deleted": 100,
            "contributors": 3,
        },
        {
            "evidence_id": id_gen.next_id("chn"),
            "path": "src/other.py",
            "window": "90d",
            "commits": 1,
            "lines_added": 10,
            "lines_deleted": 5,
            "contributors": 1,
        },
    ]

    _seed_evidence(run_handle, findings, coverage, churn)

    reader = EvidenceReader(run_handle)
    config = RiskConfig(weights=RiskWeights(security=3.0, coverage=2.0, churn=2.0))
    aggregator = RiskAggregator(config)
    writer = EvidenceWriter(run_handle)
    risks = aggregator.aggregate(reader, writer, id_gen)

    assert risks
    by_component = {risk.component: risk for risk in risks}
    assert "src/auth/login.py" in by_component
    auth_risk = by_component["src/auth/login.py"]
    assert auth_risk.score > by_component["src/other.py"].score
    assert auth_risk.confidence > 0
    assert auth_risk.band in {"P0", "P1", "P2", "P3"}


def test_risk_aggregator_handles_no_evidence(run_handle):
    reader = EvidenceReader(run_handle)
    aggregator = RiskAggregator(RiskConfig())
    writer = EvidenceWriter(run_handle)
    id_gen = EvidenceIDGenerator(run_handle.run_id)

    risks = aggregator.aggregate(reader, writer, id_gen)
    assert risks == []
