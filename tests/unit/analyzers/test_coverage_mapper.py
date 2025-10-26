from __future__ import annotations

from dataclasses import dataclass

import pytest

from qaagent.analyzers.coverage_mapper import CoverageMapper
from qaagent.analyzers.cuj_config import CUJ, CUJConfig


@dataclass
class DummyCoverageRecord:
    component: str
    value: float


def test_coverage_mapper_matches_patterns() -> None:
    config = CUJConfig(
        product="test",
        journeys=[
            CUJ(id="auth", name="Auth", components=["src/auth/*", "src/api/auth/*"]),
            CUJ(id="other", name="Other", components=["src/other/*"]),
        ],
        coverage_targets={"auth": 80, "other": 50},
    )
    mapper = CoverageMapper(config)

    records = [
        DummyCoverageRecord(component="src/auth/login.py", value=0.6),
        DummyCoverageRecord(component="src/auth/session.py", value=0.4),
        DummyCoverageRecord(component="src/other/foo.py", value=0.9),
    ]

    cuj_coverage = mapper.map_coverage(records)
    coverage_by_id = {item.journey.id: item for item in cuj_coverage}

    assert coverage_by_id["auth"].coverage == pytest.approx((0.6 + 0.4) / 2)
    assert coverage_by_id["auth"].target == 0.8
    assert "src/auth/login.py" in coverage_by_id["auth"].components
    assert coverage_by_id["other"].coverage == pytest.approx(0.9)
    assert coverage_by_id["other"].target == 0.5
