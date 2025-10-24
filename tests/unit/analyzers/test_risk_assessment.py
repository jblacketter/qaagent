from __future__ import annotations

from qaagent.analyzers.models import RiskCategory, RiskSeverity, Route
from qaagent.analyzers.risk_assessment import assess_risks, risks_to_markdown


def make_route(method: str, path: str, **kwargs) -> Route:
    defaults = {
        "auth_required": False,
        "summary": None,
        "description": None,
        "tags": [],
        "params": {},
        "responses": {},
    }
    defaults.update(kwargs)
    return Route(method=method, path=path, **defaults)


def test_assess_risks_detects_missing_authentication() -> None:
    routes = [
        make_route("POST", "/admin/users", auth_required=False),
        make_route("GET", "/public", auth_required=False),
    ]

    risks = assess_risks(routes)
    assert any(risk.category == RiskCategory.SECURITY for risk in risks)
    auth_risk = next(r for r in risks if r.category == RiskCategory.SECURITY)
    assert auth_risk.severity == RiskSeverity.CRITICAL
    assert auth_risk.cwe_id == "CWE-306"


def test_assess_risks_detects_missing_pagination() -> None:
    routes = [make_route("GET", "/api/list", params={"query": []})]
    risks = assess_risks(routes)
    perf_risk = next(r for r in risks if r.category == RiskCategory.PERFORMANCE)
    assert "pagination" in perf_risk.description.lower()


def test_risks_to_markdown_handles_empty() -> None:
    assert "No risks" in risks_to_markdown([])
