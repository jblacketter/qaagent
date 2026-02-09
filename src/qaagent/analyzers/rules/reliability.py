"""Reliability risk rules (REL-001 through REL-004)."""
from __future__ import annotations

import re
from collections import Counter
from typing import List, Optional

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route

from .base import RiskRule


class REL001_DeprecatedOperation(RiskRule):
    rule_id = "REL-001"
    category = RiskCategory.RELIABILITY
    severity = RiskSeverity.LOW
    title = "Deprecated route"
    description = "Deprecated endpoints should be removed or replaced."

    def evaluate(self, route: Route) -> Optional[Risk]:
        if route.metadata.get("deprecated"):
            return Risk(
                category=self.category,
                severity=self.severity,
                route=f"{route.method} {route.path}",
                title=self.title,
                description="Deprecated endpoints should be removed or replaced to avoid drift.",
                recommendation="Plan to remove or replace deprecated endpoints and update clients.",
                source=self.rule_id,
            )
        return None


class REL002_MissingErrorSchema(RiskRule):
    rule_id = "REL-002"
    category = RiskCategory.RELIABILITY
    severity = RiskSeverity.LOW
    title = "Missing error response schema"
    description = "Endpoints without defined error response schemas."

    def evaluate(self, route: Route) -> Optional[Risk]:
        responses = route.responses
        if not responses:
            return None
        # Check for 4xx/5xx response definitions
        error_codes = {k for k in responses if k.startswith(("4", "5"))}
        if error_codes:
            return None
        # Only flag mutation endpoints (GETs are less critical)
        if route.method == "GET":
            return None
        return Risk(
            category=self.category,
            severity=self.severity,
            route=f"{route.method} {route.path}",
            title=self.title,
            description="Mutation endpoints without defined error responses make client error handling unreliable.",
            recommendation="Define 400, 404, and 500 error response schemas with structured error bodies.",
            source=self.rule_id,
        )


class REL003_InconsistentNaming(RiskRule):
    """Aggregate rule: checks naming consistency across all routes."""

    rule_id = "REL-003"
    category = RiskCategory.RELIABILITY
    severity = RiskSeverity.LOW
    title = "Inconsistent path naming conventions"
    description = "API paths use mixed naming conventions."

    def evaluate_all(self, routes: List[Route]) -> List[Risk]:
        if not routes:
            return []

        # Classify each path segment naming style
        styles: Counter = Counter()
        for route in routes:
            segments = [s for s in route.path.split("/") if s and not s.startswith("{")]
            for seg in segments:
                if "_" in seg:
                    styles["snake_case"] += 1
                elif "-" in seg:
                    styles["kebab-case"] += 1
                elif seg != seg.lower():
                    styles["camelCase"] += 1
                else:
                    styles["lowercase"] += 1

        # If there are multiple non-lowercase styles, flag it
        named_styles = {k: v for k, v in styles.items() if k != "lowercase"}
        if len(named_styles) > 1:
            style_summary = ", ".join(f"{k}({v})" for k, v in named_styles.items())
            return [
                Risk(
                    category=self.category,
                    severity=self.severity,
                    route=None,
                    title=self.title,
                    description=f"API paths use mixed naming conventions: {style_summary}. This impacts developer experience.",
                    recommendation="Standardize on one naming convention (kebab-case is recommended for URLs).",
                    source=self.rule_id,
                )
            ]
        return []


class REL004_MissingHealthCheck(RiskRule):
    """Aggregate rule: checks for health/readiness endpoint presence."""

    rule_id = "REL-004"
    category = RiskCategory.RELIABILITY
    severity = RiskSeverity.MEDIUM
    title = "Missing health check endpoint"
    description = "No health/readiness endpoint found."

    def evaluate_all(self, routes: List[Route]) -> List[Risk]:
        if not routes:
            return []

        health_patterns = {"/health", "/healthz", "/ready", "/readiness", "/ping", "/status", "/livez"}
        paths = {route.path.lower().rstrip("/") for route in routes}

        if any(pattern in path for path in paths for pattern in health_patterns):
            return []

        return [
            Risk(
                category=self.category,
                severity=self.severity,
                route=None,
                title=self.title,
                description="No health check endpoint found. Health endpoints are essential for load balancers and orchestrators.",
                recommendation="Add a /health or /healthz endpoint that returns 200 when the service is ready.",
                source=self.rule_id,
            )
        ]
