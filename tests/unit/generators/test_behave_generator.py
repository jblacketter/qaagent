from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

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
    result = generator.generate()

    feature_path = result.files.get("feature:pets")
    assert feature_path and feature_path.exists()
    feature_text = feature_path.read_text(encoding="utf-8")
    assert "Feature:" in feature_text
    assert "Scenario:" in feature_text

    steps_path = result.files.get("steps")
    assert steps_path and steps_path.exists()
    steps_text = steps_path.read_text(encoding="utf-8")
    assert "@when('I send a" in steps_text


def test_behave_retrieval_context_passed_to_enhancer(tmp_path: Path) -> None:
    route = sample_route(path="/pets", method="POST")
    risk = sample_risk()
    generator = BehaveGenerator(
        routes=[route],
        risks=[risk],
        output_dir=tmp_path,
        retrieval_context=["docs/security.md:1-2\nauth required"],
    )
    mock_enhancer = MagicMock()
    mock_enhancer.generate_response_assertions.return_value = ["the response body should include id"]
    mock_enhancer.generate_step_definitions.return_value = ["the response status should be 401"]
    generator._get_enhancer = lambda: mock_enhancer  # type: ignore[method-assign]

    _ = generator._baseline_scenario(route)
    _ = generator._scenario_from_risk(route, risk)

    assert (
        mock_enhancer.generate_response_assertions.call_args.kwargs["retrieval_context"]
        == generator.retrieval_context
    )
    assert (
        mock_enhancer.generate_step_definitions.call_args.kwargs["retrieval_context"]
        == generator.retrieval_context
    )
