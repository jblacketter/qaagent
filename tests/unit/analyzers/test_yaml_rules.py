"""Tests for YamlRiskRule condition matching and severity escalation."""
from __future__ import annotations

import pytest

from qaagent.analyzers.models import RiskCategory, RiskSeverity, Route
from qaagent.analyzers.rules.yaml_loader import CustomRuleDefinition
from qaagent.analyzers.rules.yaml_rule import YamlRiskRule


def _route(**kwargs) -> Route:
    defaults = {
        "path": "/api/test",
        "method": "GET",
        "auth_required": False,
        "tags": [],
    }
    defaults.update(kwargs)
    return Route(**defaults)


def _rule(match: dict, **overrides) -> YamlRiskRule:
    base = {
        "rule_id": "TEST-001",
        "category": "security",
        "severity": "medium",
        "title": "Test Rule",
        "description": "Test description",
        "recommendation": "Test recommendation",
        "match": match,
    }
    base.update(overrides)
    return YamlRiskRule(CustomRuleDefinition.model_validate(base))


# ------------------------------------------------------------------
# Path conditions
# ------------------------------------------------------------------


class TestPathConditions:
    def test_equals_match(self):
        rule = _rule({"path": {"equals": "/api/test"}})
        assert rule.evaluate(_route()) is not None

    def test_equals_no_match(self):
        rule = _rule({"path": {"equals": "/other"}})
        assert rule.evaluate(_route()) is None

    def test_contains_match(self):
        rule = _rule({"path": {"contains": "/api"}})
        assert rule.evaluate(_route()) is not None

    def test_contains_no_match(self):
        rule = _rule({"path": {"contains": "/admin"}})
        assert rule.evaluate(_route()) is None

    def test_regex_match(self):
        rule = _rule({"path": {"regex": "^/api/.*"}})
        assert rule.evaluate(_route()) is not None

    def test_regex_no_match(self):
        rule = _rule({"path": {"regex": "^/admin/.*"}})
        assert rule.evaluate(_route()) is None

    def test_starts_with_match(self):
        rule = _rule({"path": {"starts_with": "/api/"}})
        assert rule.evaluate(_route()) is not None

    def test_starts_with_no_match(self):
        rule = _rule({"path": {"starts_with": "/admin/"}})
        assert rule.evaluate(_route()) is None

    def test_not_contains_match(self):
        rule = _rule({"path": {"not_contains": ["/admin", "/internal"]}})
        assert rule.evaluate(_route()) is not None

    def test_not_contains_no_match(self):
        rule = _rule({"path": {"not_contains": ["/api", "/internal"]}})
        assert rule.evaluate(_route()) is None

    def test_combined_path_conditions(self):
        rule = _rule({"path": {"starts_with": "/api/", "contains": "test"}})
        assert rule.evaluate(_route()) is not None

    def test_combined_path_conditions_partial_fail(self):
        rule = _rule({"path": {"starts_with": "/api/", "contains": "admin"}})
        assert rule.evaluate(_route()) is None


# ------------------------------------------------------------------
# Method conditions
# ------------------------------------------------------------------


class TestMethodConditions:
    def test_equals_match(self):
        rule = _rule({"method": {"equals": "GET"}})
        assert rule.evaluate(_route()) is not None

    def test_equals_no_match(self):
        rule = _rule({"method": {"equals": "POST"}})
        assert rule.evaluate(_route()) is None

    def test_in_match(self):
        rule = _rule({"method": {"in": ["GET", "POST"]}})
        assert rule.evaluate(_route()) is not None

    def test_in_no_match(self):
        rule = _rule({"method": {"in": ["POST", "PUT"]}})
        assert rule.evaluate(_route()) is None


# ------------------------------------------------------------------
# Auth conditions
# ------------------------------------------------------------------


class TestAuthConditions:
    def test_equals_false_match(self):
        rule = _rule({"auth_required": {"equals": False}})
        assert rule.evaluate(_route(auth_required=False)) is not None

    def test_equals_false_no_match(self):
        rule = _rule({"auth_required": {"equals": False}})
        assert rule.evaluate(_route(auth_required=True)) is None

    def test_equals_true_match(self):
        rule = _rule({"auth_required": {"equals": True}})
        assert rule.evaluate(_route(auth_required=True)) is not None


# ------------------------------------------------------------------
# Tags conditions
# ------------------------------------------------------------------


class TestTagsConditions:
    def test_contains_match(self):
        rule = _rule({"tags": {"contains": "admin"}})
        assert rule.evaluate(_route(tags=["admin", "v1"])) is not None

    def test_contains_no_match(self):
        rule = _rule({"tags": {"contains": "admin"}})
        assert rule.evaluate(_route(tags=["user", "v1"])) is None

    def test_empty_true_match(self):
        rule = _rule({"tags": {"empty": True}})
        assert rule.evaluate(_route(tags=[])) is not None

    def test_empty_true_no_match(self):
        rule = _rule({"tags": {"empty": True}})
        assert rule.evaluate(_route(tags=["v1"])) is None

    def test_empty_false_match(self):
        rule = _rule({"tags": {"empty": False}})
        assert rule.evaluate(_route(tags=["v1"])) is not None

    def test_empty_false_no_match(self):
        rule = _rule({"tags": {"empty": False}})
        assert rule.evaluate(_route(tags=[])) is None


# ------------------------------------------------------------------
# Deprecated conditions
# ------------------------------------------------------------------


class TestDeprecatedConditions:
    def test_equals_true_match(self):
        rule = _rule({"deprecated": {"equals": True}})
        assert rule.evaluate(_route(metadata={"deprecated": True})) is not None

    def test_equals_true_no_match(self):
        rule = _rule({"deprecated": {"equals": True}})
        assert rule.evaluate(_route()) is None

    def test_equals_false_match(self):
        rule = _rule({"deprecated": {"equals": False}})
        assert rule.evaluate(_route()) is not None


# ------------------------------------------------------------------
# Multi-condition AND logic
# ------------------------------------------------------------------


class TestMultiCondition:
    def test_all_match(self):
        rule = _rule({
            "path": {"contains": "/api"},
            "method": {"equals": "POST"},
            "auth_required": {"equals": False},
        })
        assert rule.evaluate(_route(method="POST")) is not None

    def test_one_fails(self):
        rule = _rule({
            "path": {"contains": "/api"},
            "method": {"equals": "POST"},
            "auth_required": {"equals": True},
        })
        assert rule.evaluate(_route(method="POST")) is None

    def test_empty_match_matches_everything(self):
        rule = _rule({})
        assert rule.evaluate(_route()) is not None


# ------------------------------------------------------------------
# Severity escalation
# ------------------------------------------------------------------


class TestSeverityEscalation:
    def test_no_escalation(self):
        rule = _rule(
            {"path": {"contains": "/api"}},
            severity="medium",
        )
        risk = rule.evaluate(_route())
        assert risk is not None
        assert risk.severity == RiskSeverity.MEDIUM

    def test_single_escalation_match(self):
        rule = _rule(
            {"path": {"contains": "/"}},
            severity="medium",
            severity_escalation=[
                {"condition": {"path": {"contains": "admin"}}, "severity": "critical"},
            ],
        )
        risk = rule.evaluate(_route(path="/admin/users"))
        assert risk is not None
        assert risk.severity == RiskSeverity.CRITICAL

    def test_escalation_no_match_uses_base(self):
        rule = _rule(
            {"path": {"contains": "/"}},
            severity="medium",
            severity_escalation=[
                {"condition": {"path": {"contains": "admin"}}, "severity": "critical"},
            ],
        )
        risk = rule.evaluate(_route(path="/api/users"))
        assert risk is not None
        assert risk.severity == RiskSeverity.MEDIUM

    def test_first_escalation_wins(self):
        rule = _rule(
            {"path": {"contains": "/"}},
            severity="low",
            severity_escalation=[
                {"condition": {"path": {"contains": "admin"}}, "severity": "critical"},
                {"condition": {"path": {"contains": "admin"}}, "severity": "high"},
            ],
        )
        risk = rule.evaluate(_route(path="/admin/panel"))
        assert risk is not None
        assert risk.severity == RiskSeverity.CRITICAL

    def test_multiple_escalations_second_match(self):
        rule = _rule(
            {"path": {"contains": "/"}},
            severity="low",
            severity_escalation=[
                {"condition": {"method": {"equals": "DELETE"}}, "severity": "critical"},
                {"condition": {"path": {"contains": "export"}}, "severity": "high"},
            ],
        )
        risk = rule.evaluate(_route(path="/api/export"))
        assert risk is not None
        assert risk.severity == RiskSeverity.HIGH


# ------------------------------------------------------------------
# Risk output fields
# ------------------------------------------------------------------


class TestRiskOutput:
    def test_risk_fields(self):
        rule = _rule(
            {"path": {"contains": "/api"}},
            rule_id="CUSTOM-099",
            category="performance",
            severity="high",
            title="My Title",
            description="My Desc",
            recommendation="My Rec",
            cwe_id="CWE-123",
            owasp_top_10="A01:2021",
            references=["https://example.com"],
        )
        risk = rule.evaluate(_route(method="POST", path="/api/data"))
        assert risk is not None
        assert risk.source == "CUSTOM-099"
        assert risk.category == RiskCategory.PERFORMANCE
        assert risk.severity == RiskSeverity.HIGH
        assert risk.title == "My Title"
        assert risk.description == "My Desc"
        assert risk.recommendation == "My Rec"
        assert risk.cwe_id == "CWE-123"
        assert risk.owasp_top_10 == "A01:2021"
        assert risk.references == ["https://example.com"]
        assert risk.route == "POST /api/data"

    def test_no_match_returns_none(self):
        rule = _rule({"path": {"equals": "/nonexistent"}})
        assert rule.evaluate(_route()) is None


# ------------------------------------------------------------------
# evaluate_all (inherited from base)
# ------------------------------------------------------------------


class TestEvaluateAll:
    def test_evaluate_all_delegates(self):
        rule = _rule({"method": {"equals": "POST"}})
        routes = [
            _route(method="POST", path="/a"),
            _route(method="GET", path="/b"),
            _route(method="POST", path="/c"),
        ]
        risks = rule.evaluate_all(routes)
        assert len(risks) == 2
        assert {r.route for r in risks} == {"POST /a", "POST /c"}
