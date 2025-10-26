"""Collector orchestration and analysis helpers."""

from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Optional, List

from qaagent.collectors.orchestrator import CollectorsOrchestrator
from qaagent.analyzers.evidence_reader import EvidenceReader
from qaagent.analyzers.risk_config import RiskConfig
from qaagent.analyzers.risk_aggregator import RiskAggregator
from qaagent.analyzers.cuj_config import CUJConfig
from qaagent.analyzers.coverage_mapper import CoverageMapper
from qaagent.analyzers.recommender import RecommendationEngine
from qaagent.evidence import (
    EvidenceWriter,
    EvidenceIDGenerator,
    RiskRecord,
    RecommendationRecord,
)
from qaagent.evidence.run_manager import RunManager, RunHandle

LOGGER = logging.getLogger(__name__)


def run_collectors(target: Path, runs_dir: Optional[Path] = None) -> str:
    """Execute all collectors against the provided target.

    Returns the run identifier for downstream use.
    """
    target = target.resolve()
    if not target.exists():
        raise FileNotFoundError(f"Target path does not exist: {target}")

    manager = RunManager(base_dir=runs_dir)
    handle = manager.create_run(target.name, target)
    writer = EvidenceWriter(handle)
    id_generator = EvidenceIDGenerator(handle.run_id)

    orchestrator = CollectorsOrchestrator()
    orchestrator.run_all(handle, writer, id_generator)

    return handle.run_id


def ensure_run_handle(run: Optional[str], runs_dir: Optional[Path]) -> RunHandle:
    manager = RunManager(base_dir=runs_dir)
    if run:
        candidate = Path(run)
        if candidate.exists():
            return manager.load_run(candidate)
        return manager.load_run(run)

    run_dirs = sorted([p for p in manager.base_dir.iterdir() if p.is_dir()], reverse=True)
    if not run_dirs:
        raise FileNotFoundError("No analysis runs found. Run 'qaagent analyze collectors' first.")
    return manager.load_run(run_dirs[0])


def _load_risk_records(handle: RunHandle) -> List[RiskRecord]:
    risk_path = handle.evidence_dir / "risks.jsonl"
    if not risk_path.exists():
        return []
    return [
        RiskRecord.from_dict(json.loads(line))
        for line in risk_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_recommendations(handle: RunHandle) -> List[RecommendationRecord]:
    rec_path = handle.evidence_dir / "recommendations.jsonl"
    if not rec_path.exists():
        return []
    return [
        RecommendationRecord.from_dict(json.loads(line))
        for line in rec_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def ensure_risks(
    run: Optional[str],
    runs_dir: Optional[Path],
    config_path: Path,
) -> tuple[RunHandle, List[RiskRecord]]:
    handle = ensure_run_handle(run, runs_dir)
    risks = _load_risk_records(handle)
    if risks:
        return handle, risks

    reader = EvidenceReader(handle)
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)
    config = RiskConfig.load(config_path)
    aggregator = RiskAggregator(config)
    risks = aggregator.aggregate(reader, writer, id_gen)
    return handle, risks


def ensure_recommendations(
    run: Optional[str],
    runs_dir: Optional[Path],
    risk_config: Path,
    cuj_config: Path,
) -> tuple[RunHandle, List[RiskRecord], List[RecommendationRecord]]:
    handle, risks = ensure_risks(run, runs_dir, risk_config)
    recs = _load_recommendations(handle)
    if recs:
        return handle, risks, recs

    reader = EvidenceReader(handle)
    coverage_records = reader.read_coverage()
    cuj_conf = CUJConfig.load(cuj_config)
    coverage_mapper = CoverageMapper(cuj_conf)
    cuj_coverage = coverage_mapper.map_coverage(coverage_records)

    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)
    engine = RecommendationEngine()
    recs = engine.generate(risks, cuj_coverage, writer, id_gen)
    return handle, risks, recs
