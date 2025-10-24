from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Risk, RiskSeverity, Route, StrategySummary


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(disabled_extensions=(".j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def build_strategy_summary(routes: Sequence[Route], risks: Sequence[Risk]) -> StrategySummary:
    total_routes = len(routes)
    critical_routes = sum(
        1
        for route in routes
        if route.auth_required and route.method in {"POST", "PUT", "DELETE"}
    )

    priorities: List[Dict] = []
    high_risks = [risk for risk in risks if risk.severity in {RiskSeverity.CRITICAL, RiskSeverity.HIGH}]
    for risk in high_risks[:5]:
        priorities.append(
            {
                "name": risk.title,
                "reason": risk.description,
                "tests_needed": 5,
                "focus": risk.route,
            }
        )

    # Default priorities if no high risks
    if not priorities and routes:
        priorities.append(
            {
                "name": "Smoke test critical routes",
                "reason": "Ensure business-critical endpoints are covered early.",
                "tests_needed": 5,
                "focus": routes[0].path,
            }
        )

    recommended_tests = {
        "unit_tests": {
            "count": max(total_routes * 3, 20),
            "focus": ["business_logic", "validation"],
        },
        "integration_tests": {
            "count": max(total_routes * 2, 10),
            "focus": ["api_contracts", "database_interactions"],
        },
        "e2e_tests": {
            "count": max(len(high_risks), 5),
            "critical_flows": [priority.get("focus") for priority in priorities[:3]],
        },
    }

    metadata = {
        "unit_test_count": 0,
        "integration_test_count": 0,
        "e2e_test_count": 0,
    }

    return StrategySummary(
        total_routes=total_routes,
        critical_routes=critical_routes,
        risks=list(risks),
        recommended_tests=recommended_tests,
        priorities=priorities,
        metadata=metadata,
    )


def _sample_scenarios(summary: StrategySummary) -> List[Dict[str, str]]:
    scenarios: List[Dict[str, str]] = []
    for risk in summary.risks[:3]:
        scenarios.append(
            {
                "name": f"Mitigate {risk.title}",
                "type": "e2e" if risk.category.name.lower() == "security" else "integration",
                "priority": risk.severity.value,
                "steps": [
                    f"Hit {risk.route} with representative data",
                    "Validate response status",
                    "Assert expected behavior or failure mode",
                ],
            }
        )
    if not scenarios and summary.total_routes:
        scenarios.append(
            {
                "name": "Verify core happy path",
                "type": "e2e",
                "priority": "high",
                "steps": [
                    "Exercise primary user flow",
                    "Assert success criteria",
                    "Capture regressions",
                ],
            }
        )
    return scenarios


def _gaps(recommended_tests: Dict[str, Dict[str, Iterable]]) -> Dict[str, int]:
    return {
        "unit_tests": recommended_tests["unit_tests"]["count"],
        "integration_tests": recommended_tests["integration_tests"]["count"],
        "e2e_tests": recommended_tests["e2e_tests"]["count"],
    }


def _effort_estimates(summary: StrategySummary) -> Dict[str, str]:
    return {
        "unit_tests": "2-3 weeks",
        "integration_tests": "1-2 weeks",
        "e2e_tests": "3-5 days",
        "total": "4-6 weeks",
    }


def render_strategy_yaml(summary: StrategySummary) -> str:
    env = _env()
    template = env.get_template("strategy.yaml.j2")
    recommended = summary.recommended_tests
    return template.render(
        summary=summary,
        recommended=recommended,
        high_risk_count=len([r for r in summary.risks if r.severity in {RiskSeverity.CRITICAL, RiskSeverity.HIGH}]),
        sample_scenarios=_sample_scenarios(summary),
        gaps=_gaps(recommended),
        effort=_effort_estimates(summary),
    )


def render_strategy_markdown(summary: StrategySummary) -> str:
    env = _env()
    template = env.get_template("strategy.md.j2")
    recommended = summary.recommended_tests
    return template.render(
        summary=summary,
        recommended=recommended,
        high_risk_count=len([r for r in summary.risks if r.severity in {RiskSeverity.CRITICAL, RiskSeverity.HIGH}]),
        sample_scenarios=_sample_scenarios(summary),
        efforts=_effort_estimates(summary),
        gaps=_gaps(recommended),
        risks=summary.risks,
        effort=_effort_estimates(summary),
    )


def export_strategy(summary: StrategySummary, yaml_path: Path, markdown_path: Optional[Path] = None) -> None:
    yaml_content = render_strategy_yaml(summary)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml_content, encoding="utf-8")

    if markdown_path:
        markdown_content = render_strategy_markdown(summary)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown_content, encoding="utf-8")
