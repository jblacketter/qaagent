"""Tests for the risk rule registry."""
from __future__ import annotations

import pytest

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route
from qaagent.analyzers.rules.base import RiskRule, RiskRuleRegistry
from qaagent.analyzers.rules import default_registry


def _route(path="/items", method="GET", auth=False, params=None):
    return Route(
        path=path,
        method=method,
        auth_required=auth,
        params=params or {},
    )


class TestRiskRuleRegistry:
    def test_register_and_list(self):
        registry = RiskRuleRegistry()
        assert len(registry.rules) == 0

        class DummyRule(RiskRule):
            rule_id = "DUMMY-001"

        registry.register(DummyRule())
        assert len(registry.rules) == 1

    def test_get_rule(self):
        registry = RiskRuleRegistry()

        class DummyRule(RiskRule):
            rule_id = "DUMMY-001"

        rule = DummyRule()
        registry.register(rule)
        assert registry.get("DUMMY-001") is rule
        assert registry.get("NONEXISTENT") is None

    def test_run_all(self):
        routes = [
            _route(path="/api/items", method="POST"),  # SEC-001: unauthenticated mutation
            _route(path="/api/users", method="GET"),    # PERF-001: missing pagination
        ]
        registry = default_registry()
        risks = registry.run_all(routes)
        assert len(risks) > 0
        rule_ids = {r.source for r in risks}
        assert "SEC-001" in rule_ids  # Unauthenticated POST

    def test_disable_rules(self):
        routes = [_route(path="/api/items", method="POST")]
        registry = default_registry()

        risks_all = registry.run_all(routes)
        risks_disabled = registry.run_all(routes, disabled={"SEC-001"})

        sec001_all = [r for r in risks_all if r.source == "SEC-001"]
        sec001_disabled = [r for r in risks_disabled if r.source == "SEC-001"]

        assert len(sec001_all) > 0
        assert len(sec001_disabled) == 0

    def test_aggregate_rules_get_full_route_list(self):
        """Aggregate rules (REL-003, REL-004) should receive all routes."""
        routes = [
            _route(path="/api/items"),
            _route(path="/api/users"),
        ]
        registry = default_registry()
        risks = registry.run_all(routes)

        # REL-004 should fire (no health endpoint)
        rel004 = [r for r in risks if r.source == "REL-004"]
        assert len(rel004) == 1

    def test_aggregate_rule_no_fire_with_health(self):
        routes = [
            _route(path="/api/items"),
            _route(path="/health"),
        ]
        registry = default_registry()
        risks = registry.run_all(routes)

        rel004 = [r for r in risks if r.source == "REL-004"]
        assert len(rel004) == 0


class TestDefaultRegistry:
    def test_has_16_rules(self):
        registry = default_registry()
        assert len(registry.rules) == 16

    def test_all_rules_have_ids(self):
        registry = default_registry()
        for rule in registry.rules:
            assert rule.rule_id, f"Rule {rule.__class__.__name__} missing rule_id"

    def test_rule_ids_are_unique(self):
        registry = default_registry()
        ids = [rule.rule_id for rule in registry.rules]
        assert len(ids) == len(set(ids)), f"Duplicate rule IDs: {ids}"


class TestBackwardCompatibility:
    """Verify existing assess_risks() behavior is preserved."""

    def test_assess_risks_still_works(self):
        from qaagent.analyzers.risk_assessment import assess_risks

        routes = [
            _route(path="/items", method="POST"),
            _route(path="/items", method="GET"),
        ]
        risks = assess_risks(routes)
        assert isinstance(risks, list)
        # SEC-001 should still fire for unauthenticated POST
        sec = [r for r in risks if "authentication" in r.title.lower() or r.source == "SEC-001"]
        assert len(sec) >= 1

    def test_assess_risks_with_disabled(self):
        from qaagent.analyzers.risk_assessment import assess_risks

        routes = [_route(path="/items", method="POST")]
        risks = assess_risks(routes, disabled_rules={"SEC-001"})
        sec001 = [r for r in risks if r.source == "SEC-001"]
        assert len(sec001) == 0
