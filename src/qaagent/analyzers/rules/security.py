"""Security risk rules (SEC-001 through SEC-008)."""
from __future__ import annotations

import re
from typing import Optional

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route

from .base import RiskRule


class SEC001_UnauthenticatedMutation(RiskRule):
    rule_id = "SEC-001"
    category = RiskCategory.SECURITY
    severity = RiskSeverity.HIGH
    title = "Unauthenticated mutation endpoint"
    description = "Mutation endpoints (POST/PUT/PATCH/DELETE) without authentication."

    def evaluate(self, route: Route) -> Optional[Risk]:
        if route.method in {"POST", "PUT", "PATCH", "DELETE"} and not route.auth_required:
            return Risk(
                category=self.category,
                severity=RiskSeverity.CRITICAL if "admin" in route.path else self.severity,
                route=f"{route.method} {route.path}",
                title=self.title,
                description="Sensitive mutation endpoints should require authentication.",
                recommendation="Require authentication and authorization checks for mutation endpoints.",
                source=self.rule_id,
                cwe_id="CWE-306",
                owasp_top_10="A07:2021",
                references=[
                    "https://cwe.mitre.org/data/definitions/306.html",
                    "https://owasp.org/Top10/A07_Identification_and_Authentication_Failures/",
                ],
            )
        return None


class SEC002_MissingCORS(RiskRule):
    rule_id = "SEC-002"
    category = RiskCategory.SECURITY
    severity = RiskSeverity.MEDIUM
    title = "Missing CORS configuration indicators"
    description = "No CORS-related metadata found on cross-origin accessible endpoints."

    def evaluate(self, route: Route) -> Optional[Risk]:
        # Heuristic: API endpoints that likely serve cross-origin requests
        if route.method == "OPTIONS":
            return None
        if not route.path.startswith("/api"):
            return None
        # Check if any CORS metadata exists
        cors_keys = {"cors", "access-control", "origin"}
        metadata_str = str(route.metadata).lower()
        if any(key in metadata_str for key in cors_keys):
            return None
        return Risk(
            category=self.category,
            severity=self.severity,
            route=f"{route.method} {route.path}",
            title=self.title,
            description="API endpoints without CORS configuration may be inaccessible from browser clients or vulnerable to CSRF.",
            recommendation="Configure CORS headers for API endpoints that serve browser clients.",
            source=self.rule_id,
            cwe_id="CWE-942",
        )


class SEC003_PathTraversal(RiskRule):
    rule_id = "SEC-003"
    category = RiskCategory.SECURITY
    severity = RiskSeverity.HIGH
    title = "Path traversal risk"
    description = "File-related path parameters without apparent validation."

    def evaluate(self, route: Route) -> Optional[Risk]:
        file_params = {"file", "filename", "filepath", "path", "document", "attachment"}
        all_params = []
        for param_list in route.params.values():
            if isinstance(param_list, list):
                all_params.extend(param_list)

        for param in all_params:
            name = param.get("name", "") if isinstance(param, dict) else str(param)
            if name.lower() in file_params:
                return Risk(
                    category=self.category,
                    severity=self.severity,
                    route=f"{route.method} {route.path}",
                    title=self.title,
                    description=f"Parameter '{name}' may allow path traversal if not validated.",
                    recommendation="Validate and sanitize file path parameters. Use allowlists and prevent directory traversal sequences.",
                    source=self.rule_id,
                    cwe_id="CWE-22",
                    owasp_top_10="A01:2021",
                )
        return None


class SEC004_MassAssignment(RiskRule):
    rule_id = "SEC-004"
    category = RiskCategory.SECURITY
    severity = RiskSeverity.MEDIUM
    title = "Mass assignment risk"
    description = "PUT/PATCH endpoints without explicit field list in request body schema."

    def evaluate(self, route: Route) -> Optional[Risk]:
        if route.method not in {"PUT", "PATCH"}:
            return None
        # Check if request body has a defined schema with explicit properties
        body_params = route.params.get("body", [])
        if body_params:
            for body in body_params:
                if isinstance(body, dict):
                    content = body.get("content", {})
                    for media in content.values():
                        schema = media.get("schema", {})
                        if schema.get("properties"):
                            return None  # Has explicit fields
        return Risk(
            category=self.category,
            severity=self.severity,
            route=f"{route.method} {route.path}",
            title=self.title,
            description="Update endpoints without explicit field lists may allow mass assignment attacks.",
            recommendation="Define explicit request body schemas with allowed fields. Reject unexpected properties.",
            source=self.rule_id,
            cwe_id="CWE-915",
            owasp_top_10="A08:2021",
        )


class SEC005_MissingRateLimit(RiskRule):
    rule_id = "SEC-005"
    category = RiskCategory.SECURITY
    severity = RiskSeverity.MEDIUM
    title = "Missing rate limiting on auth endpoint"
    description = "Authentication endpoints without apparent rate limiting."

    def evaluate(self, route: Route) -> Optional[Risk]:
        auth_paths = {"login", "signin", "auth", "token", "register", "signup", "password", "reset"}
        path_lower = route.path.lower()
        if not any(segment in path_lower for segment in auth_paths):
            return None
        if route.method not in {"POST", "PUT"}:
            return None
        return Risk(
            category=self.category,
            severity=self.severity,
            route=f"{route.method} {route.path}",
            title=self.title,
            description="Authentication endpoints without rate limiting are vulnerable to brute-force attacks.",
            recommendation="Implement rate limiting on authentication endpoints (e.g., 5 attempts per minute).",
            source=self.rule_id,
            cwe_id="CWE-307",
            owasp_top_10="A07:2021",
        )


class SEC006_SensitiveQueryParams(RiskRule):
    rule_id = "SEC-006"
    category = RiskCategory.SECURITY
    severity = RiskSeverity.HIGH
    title = "Sensitive data in query parameters"
    description = "Sensitive data (password, token, secret) passed via query string."

    def evaluate(self, route: Route) -> Optional[Risk]:
        sensitive_names = {"password", "passwd", "token", "secret", "api_key", "apikey", "access_token"}
        query_params = route.params.get("query", [])
        for param in query_params:
            name = param.get("name", "") if isinstance(param, dict) else str(param)
            if name.lower() in sensitive_names:
                return Risk(
                    category=self.category,
                    severity=self.severity,
                    route=f"{route.method} {route.path}",
                    title=self.title,
                    description=f"Parameter '{name}' in query string may be logged or cached in browser history.",
                    recommendation="Move sensitive parameters to request headers or body. Use Authorization header for tokens.",
                    source=self.rule_id,
                    cwe_id="CWE-598",
                )
        return None


class SEC007_MissingInputValidation(RiskRule):
    rule_id = "SEC-007"
    category = RiskCategory.SECURITY
    severity = RiskSeverity.MEDIUM
    title = "Missing input validation on POST/PUT body"
    description = "Mutation endpoints without request body schema definition."

    def evaluate(self, route: Route) -> Optional[Risk]:
        if route.method not in {"POST", "PUT"}:
            return None
        # If there's no body definition at all, it's suspicious
        body_params = route.params.get("body", [])
        if body_params:
            return None
        # Also skip if this looks like a simple action (no body expected)
        action_patterns = {"login", "logout", "activate", "deactivate", "toggle", "approve", "reject"}
        if any(pattern in route.path.lower() for pattern in action_patterns):
            return None
        return Risk(
            category=self.category,
            severity=self.severity,
            route=f"{route.method} {route.path}",
            title=self.title,
            description="Mutation endpoint without a defined request body schema may accept unvalidated input.",
            recommendation="Define explicit request body schemas with validation constraints.",
            source=self.rule_id,
            cwe_id="CWE-20",
            owasp_top_10="A03:2021",
        )


class SEC008_AdminWithoutElevatedAuth(RiskRule):
    rule_id = "SEC-008"
    category = RiskCategory.SECURITY
    severity = RiskSeverity.HIGH
    title = "Admin endpoint without elevated authentication"
    description = "Admin-related endpoints that may lack elevated authorization checks."

    def evaluate(self, route: Route) -> Optional[Risk]:
        admin_patterns = {"/admin", "/management", "/settings/global", "/superuser"}
        if not any(pattern in route.path.lower() for pattern in admin_patterns):
            return None
        if not route.auth_required:
            return Risk(
                category=self.category,
                severity=RiskSeverity.CRITICAL,
                route=f"{route.method} {route.path}",
                title=self.title,
                description="Admin endpoints without authentication are critically exposed.",
                recommendation="Require elevated authentication and role-based access control for admin endpoints.",
                source=self.rule_id,
                cwe_id="CWE-306",
                owasp_top_10="A01:2021",
            )
        return None
