"""Recommendation engine deriving testing priorities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from qaagent.analyzers.coverage_mapper import CujCoverage
from qaagent.evidence import RecommendationRecord, RiskRecord, EvidenceWriter, EvidenceIDGenerator


@dataclass
class RecommendationEngine:
    risk_threshold: float = 65.0
    coverage_tolerance: float = 0.05

    def generate(
        self,
        risks: Iterable[RiskRecord],
        cuj_coverage: Iterable[CujCoverage],
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> List[RecommendationRecord]:
        recommendations: List[RecommendationRecord] = []
        coverage_map = {item.journey.id: item for item in cuj_coverage}

        for risk in risks:
            priority = self._priority_from_score(risk.score)
            summary = f"Focus on {risk.component} ({priority} risk)"
            details = self._build_details(risk)
            recommendations.append(
                RecommendationRecord(
                    recommendation_id=id_generator.next_id("rec"),
                    component=risk.component,
                    priority=priority,
                    summary=summary,
                    details=details,
                    evidence_refs=risk.evidence_refs,
                    metadata={"score": risk.score, "band": risk.band},
                )
            )

        for cuj_id, coverage in coverage_map.items():
            if coverage.coverage < coverage.target - self.coverage_tolerance:
                gap = max(0.0, coverage.target - coverage.coverage)
                summary = f"Increase coverage for {coverage.journey.name}"
                details = (
                    f"Coverage for CUJ '{coverage.journey.name}' is {coverage.coverage:.0%} "
                    f"(target {coverage.target:.0%}). Focus on components: {', '.join(coverage.components)}"
                )
                recommendations.append(
                    RecommendationRecord(
                        recommendation_id=id_generator.next_id("rec"),
                        component=cuj_id,
                        priority="high",
                        summary=summary,
                        details=details,
                        evidence_refs=list(coverage.components.keys()),
                        metadata={"coverage": coverage.coverage, "target": coverage.target},
                    )
                )

        if recommendations:
            writer.write_records("recommendations", [rec.to_dict() for rec in recommendations])
        return recommendations

    def _priority_from_score(self, score: float) -> str:
        if score >= 80:
            return "critical"
        if score >= 65:
            return "high"
        if score >= 50:
            return "medium"
        return "low"

    def _build_details(self, risk: RiskRecord) -> str:
        return (
            f"Risk score {risk.score:.1f} (band {risk.band}). "
            f"Factors: {', '.join(f"{k}={v:.1f}" for k, v in risk.factors.items())}"
        )
