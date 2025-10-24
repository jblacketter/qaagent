from __future__ import annotations

import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List, Sequence

from .models import Risk, RiskCategory, RiskSeverity, Route, SEVERITY_SCORES


def _missing_authentication(route: Route) -> Risk | None:
    if route.method in {"POST", "PUT", "PATCH", "DELETE"} and not route.auth_required:
        return Risk(
            category=RiskCategory.SECURITY,
            severity=RiskSeverity.CRITICAL if "admin" in route.path else RiskSeverity.HIGH,
            route=f"{route.method} {route.path}",
            title="Mutation endpoint without authentication",
            description="Sensitive mutation endpoints should require authentication.",
            recommendation="Require authentication and authorization checks for mutation endpoints.",
            cwe_id="CWE-306",
            owasp_top_10="A07:2021",
            references=[
                "https://cwe.mitre.org/data/definitions/306.html",
                "https://owasp.org/Top10/A07_Identification_and_Authentication_Failures/",
            ],
        )
    return None


def _missing_pagination(route: Route) -> Risk | None:
    if route.method != "GET":
        return None
    params = route.params.get("query", [])
    names = {param.get("name", "").lower() for param in params}
    if any(name in names for name in {"limit", "page", "per_page", "cursor"}):
        return None
    if any(keyword in route.path for keyword in ("/search", "/list", "/all")):
        severity = RiskSeverity.HIGH
    else:
        severity = RiskSeverity.MEDIUM
    return Risk(
        category=RiskCategory.PERFORMANCE,
        severity=severity,
        route=f"{route.method} {route.path}",
        title="Potential missing pagination",
        description="Large collection endpoints without pagination can exhaust resources.",
        recommendation="Introduce limit/offset or cursor-based pagination for collection endpoints.",
        references=["https://restfulapi.net/pagination/"],
    )


def _deprecated_operation(route: Route) -> Risk | None:
    if route.metadata.get("deprecated"):
        return Risk(
            category=RiskCategory.RELIABILITY,
            severity=RiskSeverity.LOW,
            route=f"{route.method} {route.path}",
            title="Deprecated route",
            description="Deprecated endpoints should be removed or replaced to avoid drift.",
            recommendation="Plan to remove or replace deprecated endpoints and update clients.",
        )
    return None


RULES = [
    _missing_authentication,
    _missing_pagination,
    _deprecated_operation,
]


def assess_risks(routes: Sequence[Route]) -> List[Risk]:
    risks: List[Risk] = []
    for route in routes:
        for rule in RULES:
            risk = rule(route)
            if risk:
                risks.append(risk)

    # Prioritise by severity, then by heuristics (admin routes higher priority)
    prioritized = sorted(
        risks,
        key=lambda r: (SEVERITY_SCORES.get(r.severity, 0), "admin" in (r.route or "")),
        reverse=True,
    )
    return prioritized


def risks_to_markdown(risks: Iterable[Risk]) -> str:
    lines = ["# Risk Assessment", ""]
    if not risks:
        lines.append("No risks identified. ✅")
        return "\n".join(lines)

    grouped: dict[RiskCategory, List[Risk]] = defaultdict(list)
    for risk in risks:
        grouped[risk.category].append(risk)

    severity_order = {
        RiskSeverity.CRITICAL: 0,
        RiskSeverity.HIGH: 1,
        RiskSeverity.MEDIUM: 2,
        RiskSeverity.LOW: 3,
        RiskSeverity.INFO: 4,
    }

    for category in sorted(grouped, key=lambda c: c.value):
        lines.append(f"## {category.value.title()} Risks")
        category_risks = sorted(grouped[category], key=lambda r: severity_order[r.severity])
        for risk in category_risks:
            lines.append(f"### {risk.title}")
            lines.append(f"- **Route**: {risk.route or 'N/A'}")
            lines.append(f"- **Severity**: `{risk.severity.value}`")
            if risk.cwe_id:
                lines.append(f"- **CWE**: {risk.cwe_id}")
            if risk.owasp_top_10:
                lines.append(f"- **OWASP Top 10**: {risk.owasp_top_10}")
            lines.append("")
            lines.append(textwrap.fill(risk.description, width=100))
            lines.append("")
            lines.append("**Recommendation**")
            lines.append(textwrap.fill(risk.recommendation, width=100))
            if risk.references:
                lines.append("")
                lines.append("**References**")
                for ref in risk.references:
                    lines.append(f"- {ref}")
            lines.append("")
        lines.append("")
    return "\n".join(lines).strip()


def export_risks_json(risks: Sequence[Risk], dest: Path) -> None:
    import json

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps([risk.to_dict() for risk in risks], indent=2), encoding="utf-8")


def export_risks_markdown(risks: Sequence[Risk], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(risks_to_markdown(risks), encoding="utf-8")
