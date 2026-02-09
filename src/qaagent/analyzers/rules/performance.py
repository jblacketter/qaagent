"""Performance risk rules (PERF-001 through PERF-004)."""
from __future__ import annotations

import re
from typing import Optional

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route

from .base import RiskRule


class PERF001_MissingPagination(RiskRule):
    rule_id = "PERF-001"
    category = RiskCategory.PERFORMANCE
    severity = RiskSeverity.MEDIUM
    title = "Potential missing pagination"
    description = "Collection endpoints without pagination parameters."

    def evaluate(self, route: Route) -> Optional[Risk]:
        if route.method != "GET":
            return None
        params = route.params.get("query", [])
        names = set()
        for param in params:
            name = param.get("name", "") if isinstance(param, dict) else str(param)
            names.add(name.lower())
        if any(name in names for name in {"limit", "page", "per_page", "cursor", "offset", "page_size"}):
            return None
        if any(keyword in route.path for keyword in ("/search", "/list", "/all")):
            severity = RiskSeverity.HIGH
        else:
            severity = self.severity
        return Risk(
            category=self.category,
            severity=severity,
            route=f"{route.method} {route.path}",
            title=self.title,
            description="Large collection endpoints without pagination can exhaust resources.",
            recommendation="Introduce limit/offset or cursor-based pagination for collection endpoints.",
            source=self.rule_id,
            references=["https://restfulapi.net/pagination/"],
        )


class PERF002_UnboundedQuery(RiskRule):
    rule_id = "PERF-002"
    category = RiskCategory.PERFORMANCE
    severity = RiskSeverity.MEDIUM
    title = "Unbounded query parameters"
    description = "Query params without max value constraint."

    def evaluate(self, route: Route) -> Optional[Risk]:
        if route.method != "GET":
            return None
        query_params = route.params.get("query", [])
        for param in query_params:
            if not isinstance(param, dict):
                continue
            name = param.get("name", "").lower()
            if name in {"limit", "page_size", "per_page", "size"}:
                # Only flag when there's an explicit schema block without maximum
                schema = param.get("schema")
                if isinstance(schema, dict) and not schema.get("maximum"):
                    return Risk(
                        category=self.category,
                        severity=self.severity,
                        route=f"{route.method} {route.path}",
                        title=self.title,
                        description=f"Parameter '{name}' has no maximum constraint, allowing clients to request unbounded result sets.",
                        recommendation=f"Set a maximum value for '{name}' (e.g., maximum: 100) to prevent resource exhaustion.",
                        source=self.rule_id,
                    )
        return None


class PERF003_N1Risk(RiskRule):
    rule_id = "PERF-003"
    category = RiskCategory.PERFORMANCE
    severity = RiskSeverity.MEDIUM
    title = "N+1 query risk on nested resource"
    description = "Nested resource endpoints that may trigger N+1 database queries."

    def evaluate(self, route: Route) -> Optional[Risk]:
        if route.method != "GET":
            return None
        # Detect nested resources: /parents/{id}/children
        parts = [p for p in route.path.split("/") if p]
        param_count = sum(1 for p in parts if p.startswith("{"))
        segment_count = len(parts)
        # Nested resource heuristic: at least 3 segments with a param in the middle
        if segment_count >= 3 and param_count >= 1:
            # Check if there's a collection after a param: /users/{id}/posts
            for i, part in enumerate(parts):
                if part.startswith("{") and i + 1 < len(parts) and not parts[i + 1].startswith("{"):
                    return Risk(
                        category=self.category,
                        severity=self.severity,
                        route=f"{route.method} {route.path}",
                        title=self.title,
                        description=f"Nested resource endpoint may require eager loading to avoid N+1 queries.",
                        recommendation="Use eager loading (JOIN/prefetch) for nested resource endpoints. Consider denormalization for frequently accessed nested data.",
                        source=self.rule_id,
                    )
        return None


class PERF004_MissingCaching(RiskRule):
    rule_id = "PERF-004"
    category = RiskCategory.PERFORMANCE
    severity = RiskSeverity.LOW
    title = "Missing caching headers on GET endpoint"
    description = "GET endpoints without apparent caching strategy."

    def evaluate(self, route: Route) -> Optional[Risk]:
        if route.method != "GET":
            return None
        # Check responses for cache-related headers
        for status, response in route.responses.items():
            if isinstance(response, dict):
                headers = response.get("headers", {})
                if any(h.lower() in {"cache-control", "etag", "last-modified"} for h in headers):
                    return None
        # Only flag stable resource endpoints (not search, not list)
        if any(pattern in route.path for pattern in ("/search", "/list", "/recent", "/latest")):
            return None
        # Only flag endpoints with path params (specific resources)
        if "{" not in route.path:
            return None
        return Risk(
            category=self.category,
            severity=self.severity,
            route=f"{route.method} {route.path}",
            title=self.title,
            description="Specific resource GET endpoints benefit from caching headers to reduce load.",
            recommendation="Add Cache-Control, ETag, or Last-Modified headers for cacheable GET endpoints.",
            source=self.rule_id,
        )
