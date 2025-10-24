from __future__ import annotations

from pathlib import Path

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route
from qaagent.generators.behave_generator import BehaveGenerator


def sample_route(path: str = "/pets", method: str = "GET") -> Route:
    return Route(
        path=path,
        method=method,
        auth_required=False,
        summary="List pets",
        tags=["pets"],
        params={},
        responses={"200": {"description": "OK"}},
    )


def sample_risk() -> Risk:
    return Risk(
        category=RiskCategory.SECURITY,
        severity=RiskSeverity.HIGH,
        route="POST /pets",
        title="Mutation endpoint without authentication",
        description="Sensitive mutation endpoints should require authentication.",
        recommendation="Add authentication middleware.",
    )


def test_behave_generator_creates_feature_files(tmp_path: Path) -> None:
    routes = [sample_route(), sample_route(path="/pets", method="POST")]
    risks = [sample_risk()]
    generator = BehaveGenerator(routes=routes, risks=risks, output_dir=tmp_path, base_url="http://localhost:8765")
    outputs = generator.generate()

    feature_path = outputs.get("feature:pets")
    assert feature_path and feature_path.exists()
    feature_text = feature_path.read_text(encoding="utf-8")
    assert "Feature:" in feature_text
    assert "Scenario:" in feature_text

    steps_path = outputs.get("steps")
    assert steps_path and steps_path.exists()
    steps_text = steps_path.read_text(encoding="utf-8")
    assert "@when('I send a" in steps_text
