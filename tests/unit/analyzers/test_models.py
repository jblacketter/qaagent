from __future__ import annotations

from qaagent.analyzers.models import (
    Risk,
    RiskCategory,
    RiskSeverity,
    Route,
    RouteSource,
    StrategySummary,
)


def test_route_serialization_roundtrip() -> None:
    route = Route(
        path="/pets",
        method="GET",
        auth_required=True,
        tags=["pets"],
        params={"query": [{"name": "limit", "in": "query"}]},
        source=RouteSource.OPENAPI,
        confidence=0.9,
        metadata={"operation_id": "listPets"},
    )

    data = route.to_dict()
    clone = Route.from_dict(data)

    assert clone.path == route.path
    assert clone.method == route.method
    assert clone.auth_required is True
    assert clone.tags == ["pets"]
    assert clone.metadata["operation_id"] == "listPets"


def test_risk_to_dict_contains_score_and_references() -> None:
    risk = Risk(
        category=RiskCategory.SECURITY,
        severity=RiskSeverity.HIGH,
        route="/pets",
        title="Unauthenticated mutation",
        description="Mutation endpoint is missing authentication.",
        recommendation="Add auth middleware.",
        cwe_id="CWE-306",
        owasp_top_10="A01:2021",
        references=["https://cwe.mitre.org/data/definitions/306.html"],
    )

    data = risk.to_dict()
    assert data["category"] == "security"
    assert data["severity"] == "high"
    assert data["score"] == 4
    assert data["score"] == risk.score
    assert data["cwe_id"] == "CWE-306"
    assert "references" in data and len(data["references"]) == 1


def test_strategy_summary_to_dict() -> None:
    risk = Risk(
        category=RiskCategory.PERFORMANCE,
        severity=RiskSeverity.MEDIUM,
        route="/pets",
        title="Missing pagination",
        description="GET /pets has no pagination parameters.",
        recommendation="Add limit & offset.",
    )

    summary = StrategySummary(
        total_routes=10,
        critical_routes=3,
        risks=[risk],
        recommended_tests={"unit": {"target": 60}},
        priorities=[{"name": "Authentication"}],
    )

    data = summary.to_dict()
    assert data["total_routes"] == 10
    assert data["critical_routes"] == 3
    assert len(data["risks"]) == 1
    assert data["recommended_tests"]["unit"]["target"] == 60
