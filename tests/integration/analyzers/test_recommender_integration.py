from __future__ import annotations

import json
from pathlib import Path

from qaagent.analyzers.coverage_mapper import CoverageMapper
from qaagent.analyzers.cuj_config import CUJ, CUJConfig
from qaagent.analyzers.recommender import RecommendationEngine
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator, RiskRecord
from qaagent.evidence.run_manager import RunManager


def test_recommender_integration(tmp_path: Path) -> None:
    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("repo", tmp_path / "repo")
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)

    # Seed risks
    risks = [
        RiskRecord(
            risk_id="RSK-1",
            component="src/auth/session.py",
            score=85.0,
            band="P0",
            confidence=0.9,
            severity="critical",
            title="Auth risk",
            description="",
            evidence_refs=["FND-1"],
            factors={"security": 60.0, "coverage": 15.0, "churn": 10.0},
            recommendations=[],
        )
    ]

    # Seed coverage records
    coverage_records = [
        type("Coverage", (), {"component": "src/auth/session.py", "value": 0.3})
    ]

    cuj_config = CUJConfig(
        product="demo",
        journeys=[CUJ(id="auth_login", name="Login", components=["src/auth/*"])] ,
        coverage_targets={"auth_login": 80},
    )
    coverage_mapper = CoverageMapper(cuj_config)
    cuj_coverage = coverage_mapper.map_coverage(coverage_records)

    engine = RecommendationEngine()
    recs = engine.generate(risks, cuj_coverage, writer, id_gen)
    assert recs
    rec_file = handle.evidence_dir / "recommendations.jsonl"
    assert rec_file.exists()
    payloads = [json.loads(line) for line in rec_file.read_text().strip().splitlines()]
    assert payloads
