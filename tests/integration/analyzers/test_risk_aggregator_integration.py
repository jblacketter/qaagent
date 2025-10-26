from __future__ import annotations

import json
from pathlib import Path

from qaagent.analyzers.evidence_reader import EvidenceReader
from qaagent.analyzers.risk_aggregator import RiskAggregator
from qaagent.analyzers.risk_config import RiskConfig
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager


def _seed_synthetic_evidence(handle):
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)

    writer.write_records(
        "quality",
        [
            {
                "evidence_id": id_gen.next_id("fnd"),
                "tool": "flake8",
                "severity": "high",
                "code": "E302",
                "message": "expected blank lines",
                "file": "src/auth/session.py",
            },
            {
                "evidence_id": id_gen.next_id("fnd"),
                "tool": "flake8",
                "severity": "low",
                "code": "W291",
                "message": "trailing whitespace",
                "file": "src/other.py",
            },
        ],
    )

    writer.write_records(
        "coverage",
        [
            {
                "coverage_id": id_gen.next_id("cov"),
                "type": "line",
                "component": "src/auth/session.py",
                "value": 0.3,
            },
            {
                "coverage_id": id_gen.next_id("cov"),
                "type": "line",
                "component": "src/other.py",
                "value": 0.9,
            },
        ],
    )

    writer.write_records(
        "churn",
        [
            {
                "evidence_id": id_gen.next_id("chn"),
                "path": "src/auth/session.py",
                "window": "90d",
                "commits": 12,
                "lines_added": 80,
                "lines_deleted": 30,
                "contributors": 4,
            },
            {
                "evidence_id": id_gen.next_id("chn"),
                "path": "src/other.py",
                "window": "90d",
                "commits": 1,
                "lines_added": 5,
                "lines_deleted": 2,
                "contributors": 1,
            },
        ],
    )


def test_risk_aggregator_integration(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("repo", repo)
    _seed_synthetic_evidence(handle)

    reader = EvidenceReader(handle)
    writer = EvidenceWriter(handle)
    aggregator = RiskAggregator(RiskConfig())
    risks = aggregator.aggregate(reader, writer, EvidenceIDGenerator(handle.run_id))

    assert risks
    risks_path = handle.evidence_dir / "risks.jsonl"
    assert risks_path.exists()
    payloads = [json.loads(line) for line in risks_path.read_text().strip().splitlines()]
    assert payloads
    top = max(payloads, key=lambda x: x["score"])
    assert top["component"].endswith("src/auth/session.py")
