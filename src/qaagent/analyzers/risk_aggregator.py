"""Risk aggregation engine (Sprint 2 core logic)."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from qaagent.analyzers.evidence_reader import EvidenceReader
from qaagent.analyzers.risk_config import RiskConfig
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator, RiskRecord
from qaagent.evidence.run_manager import RunHandle, RunManager

LOGGER = logging.getLogger(__name__)


@dataclass
class RiskAggregator:
    config: RiskConfig

    def aggregate(self, reader: EvidenceReader, writer: EvidenceWriter, id_generator: EvidenceIDGenerator) -> List[RiskRecord]:
        findings = reader.read_findings()
        coverage = reader.read_coverage()
        churn = reader.read_churn()

        security_scores = self._compute_security(findings)
        coverage_scores = self._compute_coverage(coverage)
        churn_scores = self._compute_churn(churn)

        all_components = set(security_scores) | set(coverage_scores) | set(churn_scores)
        records: List[RiskRecord] = []

        for component in all_components:
            raw_factors = {
                "security": security_scores.get(component, 0.0),
                "coverage": coverage_scores.get(component, 0.0),
                "churn": churn_scores.get(component, 0.0),
            }
            factors = {
                name: value * getattr(self.config.weights, name)
                for name, value in raw_factors.items()
            }
            score = sum(factors.values())
            score = min(score, self.config.max_total)
            band = self._assign_band(score)
            present_factors = sum(1 for val in raw_factors.values() if val > 0)
            confidence = present_factors / 3.0
            severity = self._severity_from_score(score)

            title = f"{component} risk ({severity})"
            description = "Risk score derived from findings, coverage gaps, and churn."
            record = RiskRecord(
                risk_id=id_generator.next_id("rsk"),
                component=component,
                score=score,
                band=band,
                confidence=confidence,
                severity=severity,
                title=title,
                description=description,
                evidence_refs=[],
                factors=factors,
            )
            records.append(record)

        if records:
            writer.write_records("risks", [r.to_dict() for r in records])
        return records

    def _compute_security(self, findings: Iterable) -> Dict[str, float]:
        weights = {"critical": 2.0, "high": 2.0, "medium": 1.0, "low": 0.5}
        scores: Dict[str, float] = defaultdict(float)
        for finding in findings:
            severity = getattr(finding, "severity", "medium")
            if hasattr(severity, "value"):
                severity = severity.value
            weight = weights.get(str(severity).lower(), 1.0)
            component = getattr(finding, "file", None)
            if not component:
                continue
            scores[component] += weight
        return scores

    def _compute_coverage(self, coverage_records: Iterable) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for record in coverage_records:
            component = getattr(record, "component", None)
            if not component or component == "__overall__":
                continue
            value = float(getattr(record, "value", 0.0))
            scores[component] = max(0.0, 1.0 - value)
        return scores

    def _compute_churn(self, churn_records: Iterable) -> Dict[str, float]:
        raw: Dict[str, float] = {}
        for record in churn_records:
            component = getattr(record, "path", None)
            if not component:
                continue
            value = float(getattr(record, "commits", 0)) + float(getattr(record, "lines_added", 0)) + float(getattr(record, "lines_deleted", 0))
            raw[component] = raw.get(component, 0.0) + value
        if not raw:
            return {}
        min_val = min(raw.values())
        max_val = max(raw.values())
        if max_val == min_val:
            return {component: 0.0 for component in raw}
        return {component: (value - min_val) / (max_val - min_val) for component, value in raw.items()}

    def _assign_band(self, score: float) -> str:
        for band in sorted(self.config.bands, key=lambda b: b.min_score, reverse=True):
            if score >= band.min_score:
                return band.name
        return self.config.bands[-1].name

    def _severity_from_score(self, score: float) -> str:
        if score >= 80:
            return "critical"
        if score >= 65:
            return "high"
        if score >= 50:
            return "medium"
        return "low"


def aggregate_risks(run_dir: Path, config_path: Path, runs_root: Optional[Path] = None) -> List[RiskRecord]:
    manager = RunManager(base_dir=runs_root)
    handle = manager.load_run(run_dir)
    reader = EvidenceReader(handle)
    config = RiskConfig.load(config_path)
    writer = EvidenceWriter(handle)
    aggregator = RiskAggregator(config)
    return aggregator.aggregate(reader, writer, EvidenceIDGenerator(handle.run_id))
