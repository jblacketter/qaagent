"""Cross-module regression tests for source-discovered routes.

Verifies that routes from framework parsers work correctly through
downstream consumers: risk_assessment, unit_test_generator, openapi_gen.
"""
from pathlib import Path

import pytest

from qaagent.analyzers.models import Route, RouteSource
from qaagent.analyzers.risk_assessment import assess_risks
from qaagent.discovery.base import FrameworkParser, RouteParam


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "discovery"


def _make_source_route(path: str, method: str, params: dict, auth: bool = False) -> Route:
    """Create a Route as a framework parser would."""
    parser = _StubParser()
    rp = {}
    for loc, items in params.items():
        rp[loc] = [RouteParam(name=n, type=t, required=True) for n, t in items]
    return parser._normalize_route(
        path=path, method=method, params=rp, auth_required=auth,
    )


class _StubParser(FrameworkParser):
    framework_name = "stub"

    def parse(self, source_dir):
        return []

    def find_route_files(self, source_dir):
        return []


class TestNormalizationContract:
    """Verify the Route.params shape produced by _normalize_route."""

    def test_params_shape_is_dict_of_lists(self):
        route = _make_source_route(
            "/items/{item_id}", "GET",
            {"path": [("item_id", "integer")], "query": [("limit", "integer")]},
        )
        assert isinstance(route.params, dict)
        assert isinstance(route.params["path"], list)
        assert isinstance(route.params["query"], list)

    def test_param_elements_are_dicts(self):
        route = _make_source_route(
            "/items/{item_id}", "GET",
            {"path": [("item_id", "integer")]},
        )
        p = route.params["path"][0]
        assert isinstance(p, dict)
        assert p["name"] == "item_id"
        assert p["type"] == "integer"
        assert p["required"] is True

    def test_path_normalization_colon_syntax(self):
        route = _make_source_route(":id/comments", "GET", {})
        assert route.path == "{id}/comments"

    def test_path_normalization_angle_bracket_syntax(self):
        route = _make_source_route("/users/<int:user_id>", "GET",
                                    {"path": [("user_id", "integer")]})
        assert route.path == "/users/{user_id}"

    def test_source_is_code(self):
        route = _make_source_route("/test", "GET", {})
        assert route.source == RouteSource.CODE

    def test_auth_required_explicit(self):
        route_auth = _make_source_route("/admin", "GET", {}, auth=True)
        assert route_auth.auth_required is True
        route_no_auth = _make_source_route("/public", "GET", {}, auth=False)
        assert route_no_auth.auth_required is False


class TestDownstreamRiskAssessment:
    """Source-discovered routes should work through risk_assessment."""

    def test_assess_risks_with_source_routes(self):
        routes = [
            _make_source_route("/api/items", "GET", {"query": [("limit", "integer")]}),
            _make_source_route("/api/items/{id}", "GET", {"path": [("id", "integer")]}),
            _make_source_route("/api/items", "POST", {}, auth=False),
            _make_source_route("/api/items/{id}", "DELETE", {}, auth=True),
        ]
        risks = assess_risks(routes)
        assert isinstance(risks, list)
        # POST without auth should trigger missing_authentication
        sec_risks = [r for r in risks if r.category.value == "security"]
        assert len(sec_risks) >= 1

    def test_missing_pagination_detects_query_params(self):
        """Route with limit param should NOT trigger missing pagination."""
        route_with_limit = _make_source_route(
            "/api/items", "GET", {"query": [("limit", "integer")]},
        )
        risks = assess_risks([route_with_limit])
        perf_risks = [r for r in risks if r.category.value == "performance"]
        # Should not flag pagination risk since limit param exists
        assert len(perf_risks) == 0


class TestDownstreamOpenAPIGen:
    """Source-discovered routes should work through openapi_gen."""

    def test_generate_parameters(self):
        from qaagent.openapi_gen.generator import OpenAPIGenerator

        route = _make_source_route(
            "/items/{item_id}", "GET",
            {"path": [("item_id", "integer")], "query": [("limit", "string")]},
        )
        gen = OpenAPIGenerator(routes=[route])
        params = gen._generate_parameters(route)

        assert len(params) == 2
        path_param = next(p for p in params if p["in"] == "path")
        assert path_param["name"] == "item_id"
        query_param = next(p for p in params if p["in"] == "query")
        assert query_param["name"] == "limit"
