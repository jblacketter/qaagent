from __future__ import annotations

from pathlib import Path

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route
from qaagent.analyzers.strategy_generator import (
    build_strategy_summary,
    export_strategy,
    render_strategy_markdown,
    render_strategy_yaml,
)


def make_route(path: str, method: str = "GET", auth_required: bool = False) -> Route:
    return Route(path=path, method=method, auth_required=auth_required)


def make_risk(route: str) -> Risk:
    return Risk(
        category=RiskCategory.SECURITY,
        severity=RiskSeverity.HIGH,
        route=route,
        title="Test risk",
        description="Example risk for testing",
        recommendation="Add mitigation",
    )


def test_build_strategy_summary_counts_routes() -> None:
    routes = [make_route("/items"), make_route("/orders", method="POST", auth_required=True)]
    risks = [make_risk("GET /items")]

    summary = build_strategy_summary(routes, risks)
    assert summary.total_routes == 2
    assert summary.critical_routes == 1
    assert summary.recommended_tests["unit_tests"]["count"] >= 20


def test_render_strategy_yaml(tmp_path: Path) -> None:
    summary = build_strategy_summary([make_route("/items")], [make_risk("GET /items")])
    yaml_text = render_strategy_yaml(summary)
    assert "test_strategy" in yaml_text

    export_path = tmp_path / "strategy.yaml"
    export_strategy(summary, export_path)
    assert export_path.exists()


def test_render_strategy_markdown_contains_priorities() -> None:
    summary = build_strategy_summary([make_route("/items")], [make_risk("GET /items")])
    md = render_strategy_markdown(summary)
    assert "Test Strategy Summary" in md
    assert "Test risk" in md
