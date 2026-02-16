from __future__ import annotations

import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from .models import Risk, RiskCategory, RiskSeverity, Route, SEVERITY_SCORES
from .rules import default_registry


def assess_risks(
    routes: Sequence[Route],
    disabled_rules: Optional[Set[str]] = None,
    *,
    custom_rules: Optional[List[Dict[str, Any]]] = None,
    custom_rules_file: Optional[Path] = None,
    severity_overrides: Optional[Dict[str, str]] = None,
) -> List[Risk]:
    """Assess risks using the pluggable rule registry.

    Args:
        routes: Routes to evaluate.
        disabled_rules: Set of rule IDs to skip.
        custom_rules: Inline custom rule dicts from config.
        custom_rules_file: Path to a custom rules YAML file.
        severity_overrides: Map of rule_id -> severity for post-eval remapping.

    Returns:
        Risks sorted by severity (highest first).
    """
    registry = default_registry(
        custom_rules=custom_rules,
        custom_rules_file=custom_rules_file,
        severity_overrides=severity_overrides,
    )
    risks = registry.run_all(list(routes), disabled=disabled_rules)

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
