"""Loader for risk aggregation configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class RiskWeights:
    security: float = 3.0
    quality: float = 0.5  # Code quality issues (flake8, pylint) - lower weight than security
    coverage: float = 2.0
    churn: float = 2.0
    complexity: float = 1.5
    api_exposure: float = 1.0
    a11y: float = 0.5
    performance: float = 1.0


@dataclass
class RiskBand:
    name: str
    min_score: float


@dataclass
class RiskConfig:
    weights: RiskWeights = field(default_factory=RiskWeights)
    bands: List[RiskBand] = field(default_factory=lambda: [
        RiskBand("P0", 80),
        RiskBand("P1", 65),
        RiskBand("P2", 50),
        RiskBand("P3", 0),
    ])
    max_total: float = 100.0

    @classmethod
    def load(cls, path: Path) -> "RiskConfig":
        if not path.exists():
            return cls()
        with path.open(encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        scoring = data.get("scoring", {})
        weights_data = scoring.get("weights", {})
        weights = RiskWeights(**{k: float(v) for k, v in weights_data.items() if hasattr(RiskWeights, k)})

        bands_data = data.get("prioritization", {}).get("bands", [])
        bands = [RiskBand(name=band.get("name", "P3"), min_score=float(band.get("min_score", 0))) for band in bands_data]
        if not bands:
            bands = cls().bands

        max_total = float(scoring.get("caps", {}).get("max_total", cls().max_total))

        return cls(weights=weights, bands=bands, max_total=max_total)
