"""Tests for dashboard.py — generate_dashboard."""
from __future__ import annotations

from pathlib import Path

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route, RouteSource
from qaagent.dashboard import generate_dashboard


def _make_routes():
    return [
        Route(
            path="/items",
            method="GET",
            auth_required=False,
            source=RouteSource.OPENAPI,
            tags=["items"],
        ),
        Route(
            path="/items",
            method="POST",
            auth_required=True,
            source=RouteSource.OPENAPI,
            tags=["items"],
        ),
    ]


def _make_risks():
    return [
        Risk(
            category=RiskCategory.SECURITY,
            severity=RiskSeverity.HIGH,
            route="POST /items",
            title="Unauthenticated mutation",
            description="POST /items has no auth",
            recommendation="Add authentication",
        ),
        Risk(
            category=RiskCategory.PERFORMANCE,
            severity=RiskSeverity.MEDIUM,
            route="GET /items",
            title="Missing pagination",
            description="GET /items may return unbounded results",
            recommendation="Add pagination",
        ),
    ]


class TestGenerateDashboard:
    def test_creates_html_file(self, tmp_path: Path):
        routes = _make_routes()
        risks = _make_risks()
        output = tmp_path / "dashboard.html"

        result = generate_dashboard(routes, risks, output)

        assert result == output
        assert output.exists()
        content = output.read_text()
        assert "<html" in content.lower() or "<!doctype" in content.lower()

    def test_html_contains_project_name(self, tmp_path: Path):
        routes = _make_routes()
        risks = _make_risks()
        output = tmp_path / "dashboard.html"

        generate_dashboard(routes, risks, output, project_name="PetStore")

        content = output.read_text()
        assert "PetStore" in content

    def test_html_contains_risk_data(self, tmp_path: Path):
        routes = _make_routes()
        risks = _make_risks()
        output = tmp_path / "dashboard.html"

        generate_dashboard(routes, risks, output)

        content = output.read_text()
        # Check for risk-related content
        assert "security" in content.lower() or "high" in content.lower()

    def test_creates_parent_dirs(self, tmp_path: Path):
        routes = _make_routes()
        risks = _make_risks()
        output = tmp_path / "nested" / "deep" / "dashboard.html"

        result = generate_dashboard(routes, risks, output)

        assert result.exists()

    def test_empty_risks(self, tmp_path: Path):
        routes = _make_routes()
        output = tmp_path / "dashboard.html"

        generate_dashboard(routes, [], output)

        assert output.exists()

    def test_empty_routes_and_risks(self, tmp_path: Path):
        output = tmp_path / "dashboard.html"

        generate_dashboard([], [], output)

        assert output.exists()

    def test_basic_mode(self, tmp_path: Path):
        routes = _make_routes()
        risks = _make_risks()
        output = tmp_path / "dashboard.html"

        generate_dashboard(routes, risks, output, enhanced=False)

        assert output.exists()
