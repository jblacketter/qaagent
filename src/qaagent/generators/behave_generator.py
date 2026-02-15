from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..analyzers.models import Risk, RiskCategory, RiskSeverity, Route
from ..config.models import LLMSettings
from .base import BaseGenerator, GenerationResult
from .validator import TestValidator

_TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "templates" / "behave"


@dataclass
class Scenario:
    title: str
    tags: List[str]
    given: List[str]
    when_method: str
    when_path: str
    then: List[str]
    comments: List[str]


class BehaveGenerator(BaseGenerator):
    """Generate Behave feature files and supporting assets."""

    def __init__(
        self,
        routes: Iterable[Route],
        risks: Iterable[Risk],
        output_dir: Path,
        base_url: Optional[str] = None,
        project_name: str = "Application",
        llm_settings: Optional[LLMSettings] = None,
        retrieval_context: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            routes=list(routes),
            risks=list(risks),
            output_dir=output_dir,
            base_url=base_url or "http://localhost:8000",
            project_name=project_name,
            llm_settings=llm_settings,
            retrieval_context=retrieval_context,
        )
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_ROOT.parent)),
            autoescape=select_autoescape(disabled_extensions=(".j2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._enhancer = None
        self._validator = TestValidator()

    def _get_enhancer(self):
        """Lazy-init LLM enhancer."""
        if self._enhancer is None and self.llm_enabled:
            from .llm_enhancer import LLMTestEnhancer
            self._enhancer = LLMTestEnhancer(self.llm_settings)
        return self._enhancer

    def generate(self, **kwargs) -> GenerationResult:
        features_dir = self.output_dir / "features"
        steps_dir = self.output_dir / "steps"
        features_dir.mkdir(parents=True, exist_ok=True)
        steps_dir.mkdir(parents=True, exist_ok=True)

        result = GenerationResult()
        scenario_count = 0

        feature_map = self._build_feature_map()
        feature_template = self._env.get_template("behave/feature.j2")
        for resource, payload in feature_map.items():
            feature_path = features_dir / f"{resource}.feature"
            feature_content = feature_template.render(
                resource_name=resource,
                feature_title=payload["title"],
                description=payload.get("description"),
                base_url=self.base_url,
                scenarios=payload["scenarios"],
            )
            # Validate Gherkin structure
            vr = self._validator.validate_gherkin(feature_content)
            if not vr.valid:
                result.warnings.append(f"{resource}.feature: {'; '.join(vr.errors)}")

            feature_path.write_text(feature_content, encoding="utf-8")
            result.files[f"feature:{resource}"] = feature_path
            scenario_count += len(payload["scenarios"])

        steps_template = self._env.get_template("behave/steps.py.j2")
        steps_path = steps_dir / "auto_steps.py"
        steps_path.write_text(steps_template.render(), encoding="utf-8")
        result.files["steps"] = steps_path

        environment_template = self._env.get_template("behave/environment.py.j2")
        environment_path = self.output_dir / "environment.py"
        environment_path.write_text(
            environment_template.render(base_url=self.base_url), encoding="utf-8"
        )
        result.files["environment"] = environment_path

        behave_ini_template = self._env.get_template("behave/behave.ini.j2")
        behave_ini_path = self.output_dir / "behave.ini"
        behave_ini_path.write_text(behave_ini_template.render(), encoding="utf-8")
        result.files["behave_ini"] = behave_ini_path

        result.stats = {
            "tests": scenario_count,
            "files": len(result.files),
            "features": len(feature_map),
        }
        result.llm_used = self.llm_enabled and self._enhancer is not None

        return result

    # Internal helpers -------------------------------------------------

    def _build_feature_map(self) -> Dict[str, Dict[str, object]]:
        feature_map: Dict[str, Dict[str, object]] = {}
        route_lookup = {(route.method.upper(), route.path): route for route in self.routes}
        risk_groups = self._group_risks_by_route(route_lookup)

        for route in self.routes:
            resource = self._resource_name(route.path)
            feature = feature_map.setdefault(
                resource,
                {
                    "title": f"{resource.title()} API scenarios",
                    "scenarios": [],
                    "description": None,
                },
            )
            feature["scenarios"].append(self._baseline_scenario(route))

        for key, risks in risk_groups.items():
            route = route_lookup.get(key)
            if not route:
                continue
            resource = self._resource_name(route.path)
            feature = feature_map.setdefault(
                resource,
                {
                    "title": f"{resource.title()} API scenarios",
                    "scenarios": [],
                    "description": None,
                },
            )
            for risk in risks:
                scenario = self._scenario_from_risk(route, risk)
                if scenario:
                    feature["scenarios"].append(scenario)

        # Sort scenarios within each feature by title
        for data in feature_map.values():
            data["scenarios"].sort(key=lambda scenario: scenario.title)
        return feature_map

    def _group_risks_by_route(
        self, route_lookup: Dict[Tuple[str, str], Route]
    ) -> Dict[Tuple[str, str], List[Risk]]:
        groups: Dict[Tuple[str, str], List[Risk]] = {}
        for risk in self.risks:
            if not risk.route:
                continue
            parts = risk.route.split()
            if len(parts) < 2:
                continue
            method, path = parts[0].upper(), parts[1]
            key = (method, path)
            if key not in route_lookup:
                continue
            groups.setdefault(key, []).append(risk)
        return groups

    def _baseline_scenario(self, route: Route) -> Scenario:
        status = self._preferred_status_code(route)
        tags = ["smoke", route.method.lower()]
        given = ["I have API access"]
        then_steps = [f"the response status should be {status}"]
        comments = []

        # LLM-enhanced: add response body assertions instead of TODO
        enhancer = self._get_enhancer()
        if enhancer and status >= 200 and status < 300:
            body_steps = enhancer.generate_response_assertions(
                route,
                retrieval_context=self.retrieval_context,
            )
            then_steps.extend(body_steps)
        elif status >= 200 and status < 300:
            comments.append("TODO: assert response body structure")

        return Scenario(
            title=f"{route.method} {route.path} succeeds",
            tags=tags,
            given=given,
            when_method=route.method,
            when_path=route.path,
            then=then_steps,
            comments=comments,
        )

    def _scenario_from_risk(self, route: Route, risk: Risk) -> Optional[Scenario]:
        severity_tag = risk.severity.value
        base_tags = [risk.category.value, severity_tag]

        # LLM-enhanced: generate real step definitions instead of TODO comments
        enhancer = self._get_enhancer()

        if risk.category == RiskCategory.SECURITY:
            expected_status = 401 if route.method in {"POST", "PUT", "DELETE"} else 403
            if enhancer:
                then_steps = enhancer.generate_step_definitions(
                    route,
                    risk,
                    retrieval_context=self.retrieval_context,
                )
                if not any(str(expected_status) in s for s in then_steps):
                    then_steps.insert(0, f"the response status should be {expected_status}")
                comments = []
            else:
                then_steps = [f"the response status should be {expected_status}"]
                comments = ["TODO: verify error response schema"]
            return Scenario(
                title=f"Block unauthenticated access to {route.method} {route.path}",
                tags=base_tags,
                given=["I am not authenticated"],
                when_method=route.method,
                when_path=route.path,
                then=then_steps,
                comments=comments,
            )
        if risk.category == RiskCategory.PERFORMANCE:
            if enhancer:
                then_steps = enhancer.generate_step_definitions(
                    route,
                    risk,
                    retrieval_context=self.retrieval_context,
                )
                comments = []
            else:
                then_steps = ["the response status should be 200"]
                comments = ["TODO: verify pagination headers or response fields"]
            return Scenario(
                title=f"Ensure pagination is implemented for {route.path}",
                tags=base_tags,
                given=["I have API access"],
                when_method=route.method,
                when_path=route.path,
                then=then_steps,
                comments=comments,
            )
        if risk.category == RiskCategory.RELIABILITY:
            if enhancer:
                then_steps = enhancer.generate_step_definitions(
                    route,
                    risk,
                    retrieval_context=self.retrieval_context,
                )
                comments = []
            else:
                then_steps = []
                comments = ["TODO: confirm deprecated endpoints are replaced"]
            return Scenario(
                title=f"Document deprecation for {route.method} {route.path}",
                tags=base_tags,
                given=["I have API access"],
                when_method=route.method,
                when_path=route.path,
                then=then_steps,
                comments=comments,
            )
        return None

    def _resource_name(self, path: str) -> str:
        parts = [segment for segment in path.strip("/").split("/") if segment and not segment.startswith("{")]
        if parts:
            return parts[0].replace("-", "_")
        return "root"

    def _preferred_status_code(self, route: Route) -> int:
        for code in route.responses.keys():
            if isinstance(code, str) and code.isdigit():
                return int(code)
        return 200
