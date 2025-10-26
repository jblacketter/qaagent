"""Loader for Critical User Journey (CUJ) configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class CUJ:
    id: str
    name: str
    components: List[str]
    apis: List[Dict[str, str]] = field(default_factory=list)
    acceptance: List[str] = field(default_factory=list)


@dataclass
class CUJConfig:
    product: str = ""
    journeys: List[CUJ] = field(default_factory=list)
    coverage_targets: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "CUJConfig":
        if not path.exists():
            return cls()
        with path.open(encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        product = data.get("product", "")
        journeys_data = data.get("journeys", [])
        journeys = [
            CUJ(
                id=item.get("id", ""),
                name=item.get("name", item.get("id", "")),
                components=list(item.get("components", [])),
                apis=[dict(api) for api in item.get("apis", [])],
                acceptance=list(item.get("acceptance", [])),
            )
            for item in journeys_data
        ]

        coverage_targets = {}
        for key, value in (data.get("coverage_targets", {}) or {}).items():
            try:
                coverage_targets[key] = float(value)
            except (TypeError, ValueError):
                coverage_targets[key] = 0.0
        return cls(product=product, journeys=journeys, coverage_targets=coverage_targets)
