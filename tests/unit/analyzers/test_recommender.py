from __future__ import annotations

from qaagent.analyzers.coverage_mapper import CujCoverage
from qaagent.analyzers.cuj_config import CUJ
from qaagent.analyzers.recommender import RecommendationEngine
from qaagent.evidence import RecommendationRecord, RiskRecord, EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager

from pathlib import Path


def test_recommendation_engine_generates_from_risks(tmp_path: Path) -> None:
    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("repo", tmp_path / "repo")
    writer = EvidenceWriter(handle)
    engine = RecommendationEngine()
    id_gen = EvidenceIDGenerator(handle.run_id)

    risks = [
        RiskRecord(
            risk_id="RSK-1",
            component="src/auth/login.py",
            score=82.0,
            band="P0",
            confidence=0.7,
            severity="critical",
            title="High risk",
            description="",
            factors={"security": 50.0, "coverage": 12.0, "churn": 20.0},
            evidence_refs=["FND-1"],
            recommendations=[]
        )
    ]
    coverage = []

    recs = engine.generate(risks, coverage, writer, id_gen)
    assert recs
    assert recs[0].priority == "critical"
    assert (handle.evidence_dir / "recommendations.jsonl").exists()


def test_recommendation_engine_flags_coverage_gaps(tmp_path: Path) -> None:
    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("repo", tmp_path / "repo")
    writer = EvidenceWriter(handle)
    engine = RecommendationEngine()
    id_gen = EvidenceIDGenerator(handle.run_id)

    coverage = [
        CujCoverage(
            journey=CUJ(id="auth", name="Auth", components=["src/auth/*"]),
            coverage=0.4,
            target=0.8,
            components={"src/auth/login.py": 0.4},
        )
    ]

    recs = engine.generate([], coverage, writer, id_gen)
    assert any(rec.component == "auth" for rec in recs)
