"""Tests for individual risk rules."""
from __future__ import annotations

import pytest

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route, RouteSource
from qaagent.analyzers.rules.security import (
    SEC001_UnauthenticatedMutation,
    SEC002_MissingCORS,
    SEC003_PathTraversal,
    SEC004_MassAssignment,
    SEC005_MissingRateLimit,
    SEC006_SensitiveQueryParams,
    SEC007_MissingInputValidation,
    SEC008_AdminWithoutElevatedAuth,
)
from qaagent.analyzers.rules.performance import (
    PERF001_MissingPagination,
    PERF002_UnboundedQuery,
    PERF003_N1Risk,
    PERF004_MissingCaching,
)
from qaagent.analyzers.rules.reliability import (
    REL001_DeprecatedOperation,
    REL002_MissingErrorSchema,
    REL003_InconsistentNaming,
    REL004_MissingHealthCheck,
)


def _route(path="/items", method="GET", auth=False, params=None, responses=None, metadata=None):
    return Route(
        path=path,
        method=method,
        auth_required=auth,
        params=params or {},
        responses=responses or {"200": {"description": "OK"}},
        metadata=metadata or {},
    )


# --- Security rules ---

class TestSEC001:
    def test_flags_unauthenticated_post(self):
        risk = SEC001_UnauthenticatedMutation().evaluate(_route(method="POST"))
        assert risk is not None
        assert risk.source == "SEC-001"

    def test_ignores_authenticated_post(self):
        risk = SEC001_UnauthenticatedMutation().evaluate(_route(method="POST", auth=True))
        assert risk is None

    def test_ignores_get(self):
        risk = SEC001_UnauthenticatedMutation().evaluate(_route(method="GET"))
        assert risk is None

    def test_critical_for_admin(self):
        risk = SEC001_UnauthenticatedMutation().evaluate(_route(path="/admin/users", method="DELETE"))
        assert risk is not None
        assert risk.severity == RiskSeverity.CRITICAL


class TestSEC002:
    def test_flags_api_without_cors(self):
        risk = SEC002_MissingCORS().evaluate(_route(path="/api/items"))
        assert risk is not None

    def test_ignores_non_api(self):
        risk = SEC002_MissingCORS().evaluate(_route(path="/health"))
        assert risk is None

    def test_ignores_cors_metadata(self):
        risk = SEC002_MissingCORS().evaluate(
            _route(path="/api/items", metadata={"cors": "enabled"})
        )
        assert risk is None


class TestSEC003:
    def test_flags_file_param(self):
        risk = SEC003_PathTraversal().evaluate(
            _route(params={"query": [{"name": "filename"}]})
        )
        assert risk is not None

    def test_ignores_safe_params(self):
        risk = SEC003_PathTraversal().evaluate(
            _route(params={"query": [{"name": "limit"}]})
        )
        assert risk is None


class TestSEC004:
    def test_flags_put_without_body_schema(self):
        risk = SEC004_MassAssignment().evaluate(_route(method="PUT"))
        assert risk is not None

    def test_ignores_get(self):
        risk = SEC004_MassAssignment().evaluate(_route(method="GET"))
        assert risk is None


class TestSEC005:
    def test_flags_login_endpoint(self):
        risk = SEC005_MissingRateLimit().evaluate(_route(path="/api/login", method="POST"))
        assert risk is not None

    def test_ignores_non_auth_endpoint(self):
        risk = SEC005_MissingRateLimit().evaluate(_route(path="/api/items", method="POST"))
        assert risk is None


class TestSEC006:
    def test_flags_password_in_query(self):
        risk = SEC006_SensitiveQueryParams().evaluate(
            _route(params={"query": [{"name": "password"}]})
        )
        assert risk is not None

    def test_ignores_safe_query(self):
        risk = SEC006_SensitiveQueryParams().evaluate(
            _route(params={"query": [{"name": "limit"}]})
        )
        assert risk is None


class TestSEC007:
    def test_flags_post_without_body(self):
        risk = SEC007_MissingInputValidation().evaluate(_route(method="POST"))
        assert risk is not None

    def test_ignores_post_with_body(self):
        risk = SEC007_MissingInputValidation().evaluate(
            _route(method="POST", params={"body": [{"content": {}}]})
        )
        assert risk is None

    def test_ignores_login(self):
        risk = SEC007_MissingInputValidation().evaluate(_route(path="/login", method="POST"))
        assert risk is None


class TestSEC008:
    def test_flags_unauthenticated_admin(self):
        risk = SEC008_AdminWithoutElevatedAuth().evaluate(_route(path="/admin/users", method="GET"))
        assert risk is not None
        assert risk.severity == RiskSeverity.CRITICAL

    def test_ignores_authenticated_admin(self):
        risk = SEC008_AdminWithoutElevatedAuth().evaluate(_route(path="/admin/users", auth=True))
        assert risk is None

    def test_ignores_non_admin(self):
        risk = SEC008_AdminWithoutElevatedAuth().evaluate(_route(path="/items"))
        assert risk is None


# --- Performance rules ---

class TestPERF001:
    def test_flags_get_without_pagination(self):
        risk = PERF001_MissingPagination().evaluate(_route())
        assert risk is not None

    def test_ignores_with_limit(self):
        risk = PERF001_MissingPagination().evaluate(
            _route(params={"query": [{"name": "limit"}]})
        )
        assert risk is None

    def test_high_severity_for_search(self):
        risk = PERF001_MissingPagination().evaluate(_route(path="/api/search"))
        assert risk is not None
        assert risk.severity == RiskSeverity.HIGH

    def test_ignores_non_get(self):
        risk = PERF001_MissingPagination().evaluate(_route(method="POST"))
        assert risk is None


class TestPERF002:
    def test_flags_unbounded_limit_with_schema(self):
        risk = PERF002_UnboundedQuery().evaluate(
            _route(params={"query": [{"name": "limit", "schema": {"type": "integer"}}]})
        )
        assert risk is not None

    def test_ignores_bounded_limit(self):
        risk = PERF002_UnboundedQuery().evaluate(
            _route(params={"query": [{"name": "limit", "schema": {"type": "integer", "maximum": 100}}]})
        )
        assert risk is None

    def test_ignores_limit_without_schema(self):
        """Source-parser params without schema block should not trigger."""
        risk = PERF002_UnboundedQuery().evaluate(
            _route(params={"query": [{"name": "limit", "type": "integer", "required": False}]})
        )
        assert risk is None


class TestPERF003:
    def test_flags_nested_resource(self):
        risk = PERF003_N1Risk().evaluate(_route(path="/users/{id}/posts"))
        assert risk is not None

    def test_ignores_flat_resource(self):
        risk = PERF003_N1Risk().evaluate(_route(path="/users/{id}"))
        assert risk is None


class TestPERF004:
    def test_flags_resource_without_caching(self):
        risk = PERF004_MissingCaching().evaluate(_route(path="/items/{id}"))
        assert risk is not None

    def test_ignores_collection(self):
        risk = PERF004_MissingCaching().evaluate(_route(path="/items"))
        assert risk is None


# --- Reliability rules ---

class TestREL001:
    def test_flags_deprecated(self):
        risk = REL001_DeprecatedOperation().evaluate(_route(metadata={"deprecated": True}))
        assert risk is not None

    def test_ignores_active(self):
        risk = REL001_DeprecatedOperation().evaluate(_route())
        assert risk is None


class TestREL002:
    def test_flags_mutation_without_error_schema(self):
        risk = REL002_MissingErrorSchema().evaluate(_route(method="POST"))
        assert risk is not None

    def test_ignores_with_error_codes(self):
        risk = REL002_MissingErrorSchema().evaluate(
            _route(method="POST", responses={"200": {}, "400": {"description": "Bad request"}})
        )
        assert risk is None

    def test_ignores_get(self):
        risk = REL002_MissingErrorSchema().evaluate(_route())
        assert risk is None


class TestREL003:
    def test_flags_mixed_naming(self):
        routes = [
            _route(path="/user_profiles"),
            _route(path="/user-settings"),
        ]
        risks = REL003_InconsistentNaming().evaluate_all(routes)
        assert len(risks) == 1

    def test_ignores_consistent_naming(self):
        routes = [
            _route(path="/users"),
            _route(path="/items"),
        ]
        risks = REL003_InconsistentNaming().evaluate_all(routes)
        assert len(risks) == 0


class TestREL004:
    def test_flags_missing_health(self):
        routes = [
            _route(path="/api/items"),
            _route(path="/api/users"),
        ]
        risks = REL004_MissingHealthCheck().evaluate_all(routes)
        assert len(risks) == 1

    def test_ignores_with_health(self):
        routes = [
            _route(path="/api/items"),
            _route(path="/health"),
        ]
        risks = REL004_MissingHealthCheck().evaluate_all(routes)
        assert len(risks) == 0

    def test_recognizes_healthz(self):
        routes = [_route(path="/healthz")]
        risks = REL004_MissingHealthCheck().evaluate_all(routes)
        assert len(risks) == 0
