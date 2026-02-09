"""Risk rule ABC and registry."""
from __future__ import annotations

from abc import ABC
from typing import Dict, List, Optional, Set

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route


class RiskRule(ABC):
    """Base class for all risk rules.

    Per-route rules override ``evaluate()``.
    Aggregate rules override ``evaluate_all()``.
    """

    rule_id: str = ""
    category: RiskCategory = RiskCategory.SECURITY
    severity: RiskSeverity = RiskSeverity.MEDIUM
    title: str = ""
    description: str = ""

    def evaluate(self, route: Route) -> Optional[Risk]:
        """Evaluate a single route. Override for per-route rules."""
        return None

    def evaluate_all(self, routes: List[Route]) -> List[Risk]:
        """Evaluate all routes. Default delegates to evaluate() per route.

        Override for aggregate/global rules that need the full route list.
        """
        risks: List[Risk] = []
        for route in routes:
            risk = self.evaluate(route)
            if risk:
                risks.append(risk)
        return risks


class RiskRuleRegistry:
    """Registry of risk rules with enable/disable support."""

    def __init__(self) -> None:
        self._rules: Dict[str, RiskRule] = {}

    def register(self, rule: RiskRule) -> None:
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> Optional[RiskRule]:
        return self._rules.get(rule_id)

    @property
    def rules(self) -> List[RiskRule]:
        return list(self._rules.values())

    def run_all(
        self,
        routes: List[Route],
        disabled: Optional[Set[str]] = None,
    ) -> List[Risk]:
        """Run evaluate_all() on every enabled rule.

        Args:
            routes: Full list of discovered routes.
            disabled: Set of rule IDs to skip.

        Returns:
            Combined list of risks from all rules.
        """
        disabled = disabled or set()
        risks: List[Risk] = []
        for rule_id, rule in self._rules.items():
            if rule_id in disabled:
                continue
            risks.extend(rule.evaluate_all(routes))
        return risks
