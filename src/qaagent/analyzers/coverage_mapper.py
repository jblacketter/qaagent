"""Map coverage records to critical user journeys."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import Dict, Iterable, List

from qaagent.analyzers.cuj_config import CUJConfig, CUJ
from qaagent.analyzers.evidence_reader import EvidenceReader


@dataclass
class CujCoverage:
    journey: CUJ
    coverage: float
    target: float
    components: Dict[str, float]


class CoverageMapper:
    def __init__(self, config: CUJConfig) -> None:
        self.config = config

    def map_coverage(self, coverage_records: Iterable) -> List[CujCoverage]:
        journey_map = {journey.id: journey for journey in self.config.journeys}
        coverage_by_component = {record.component: record for record in coverage_records if record.component != "__overall__"}

        results: List[CujCoverage] = []
        for journey in journey_map.values():
            matched = {
                component: coverage_by_component[component].value
                for component in coverage_by_component
                if any(fnmatch.fnmatch(component, pattern) for pattern in journey.components)
            }
            if not matched:
                average = 0.0
            else:
                average = sum(matched.values()) / len(matched)
            target = self.config.coverage_targets.get(journey.id, 0.0) / 100.0
            results.append(CujCoverage(journey=journey, coverage=average, target=target, components=matched))
        return results
