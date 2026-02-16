"""YamlRiskRule — a RiskRule constructed from a YAML CustomRuleDefinition."""
from __future__ import annotations

import re
from typing import Optional, Pattern

from qaagent.analyzers.models import Risk, RiskSeverity, Route

from .base import RiskRule
from .yaml_loader import CustomRuleDefinition, MatchCondition


class YamlRiskRule(RiskRule):
    """Risk rule driven by declarative YAML conditions.

    All match conditions use AND logic — every present condition must match
    for the rule to fire.  Severity escalation rules are checked in order;
    first match wins.
    """

    def __init__(self, defn: CustomRuleDefinition) -> None:
        self.rule_id = defn.rule_id
        self.category = defn.category
        self.severity = defn.severity
        self.title = defn.title
        self.description = defn.description

        self._defn = defn
        self._path_regex: Optional[Pattern[str]] = None
        if defn.match.path and defn.match.path.regex:
            self._path_regex = re.compile(defn.match.path.regex)

        # Pre-compile escalation regexes
        self._escalation_regexes: list[Optional[Pattern[str]]] = []
        for esc in defn.severity_escalation:
            if esc.condition.path and esc.condition.path.regex:
                self._escalation_regexes.append(re.compile(esc.condition.path.regex))
            else:
                self._escalation_regexes.append(None)

    def evaluate(self, route: Route) -> Optional[Risk]:
        if not self._matches(route, self._defn.match, self._path_regex):
            return None

        severity = self._determine_severity(route)

        return Risk(
            category=self.category,
            severity=severity,
            route=f"{route.method} {route.path}",
            title=self._defn.title,
            description=self._defn.description,
            recommendation=self._defn.recommendation,
            source=self.rule_id,
            cwe_id=self._defn.cwe_id,
            owasp_top_10=self._defn.owasp_top_10,
            references=list(self._defn.references),
        )

    # ------------------------------------------------------------------
    # Condition matching
    # ------------------------------------------------------------------

    def _matches(
        self,
        route: Route,
        cond: MatchCondition,
        path_regex: Optional[Pattern[str]] = None,
    ) -> bool:
        if cond.path and not self._match_path(route.path, cond.path, path_regex):
            return False
        if cond.method and not self._match_method(route.method, cond.method):
            return False
        if cond.auth_required and not self._match_auth(route.auth_required, cond.auth_required):
            return False
        if cond.tags and not self._match_tags(route.tags, cond.tags):
            return False
        if cond.deprecated and not self._match_deprecated(route, cond.deprecated):
            return False
        return True

    @staticmethod
    def _match_path(path: str, cond, path_regex: Optional[Pattern[str]] = None) -> bool:
        if cond.equals is not None and path != cond.equals:
            return False
        if cond.contains is not None and cond.contains not in path:
            return False
        if cond.starts_with is not None and not path.startswith(cond.starts_with):
            return False
        if cond.not_contains is not None:
            if any(substr in path for substr in cond.not_contains):
                return False
        if cond.regex is not None:
            rx = path_regex or re.compile(cond.regex)
            if not rx.search(path):
                return False
        return True

    @staticmethod
    def _match_method(method: str, cond) -> bool:
        if cond.equals is not None and method != cond.equals:
            return False
        if cond.in_ is not None and method not in cond.in_:
            return False
        return True

    @staticmethod
    def _match_auth(auth_required: bool, cond) -> bool:
        if cond.equals is not None and auth_required != cond.equals:
            return False
        return True

    @staticmethod
    def _match_tags(tags: list[str], cond) -> bool:
        if cond.contains is not None and cond.contains not in tags:
            return False
        if cond.empty is True and len(tags) > 0:
            return False
        if cond.empty is False and len(tags) == 0:
            return False
        return True

    @staticmethod
    def _match_deprecated(route: Route, cond) -> bool:
        is_deprecated = route.metadata.get("deprecated", False)
        if cond.equals is not None and is_deprecated != cond.equals:
            return False
        return True

    # ------------------------------------------------------------------
    # Severity escalation
    # ------------------------------------------------------------------

    def _determine_severity(self, route: Route) -> RiskSeverity:
        for i, esc in enumerate(self._defn.severity_escalation):
            regex = self._escalation_regexes[i] if i < len(self._escalation_regexes) else None
            if self._matches(route, esc.condition, regex):
                return esc.severity
        return self._defn.severity
