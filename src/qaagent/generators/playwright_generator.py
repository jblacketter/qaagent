"""Playwright TypeScript E2E test generator.

Generates a complete Playwright + TypeScript project from routes, risks, and CUJs.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from qaagent.analyzers.cuj_config import CUJ
from qaagent.analyzers.models import Risk, Route
from qaagent.config.models import AuthSettings, LLMSettings
from qaagent.generators.base import BaseGenerator, GenerationResult
from qaagent.generators.validator import TestValidator

logger = logging.getLogger(__name__)

_TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "templates"

# Playwright device registry uses these exact keys
BROWSER_DEVICE_MAP: Dict[str, str] = {
    "chromium": "Desktop Chrome",
    "firefox": "Desktop Firefox",
    "webkit": "Desktop Safari",
}


class PlaywrightGenerator(BaseGenerator):
    """Generate a Playwright + TypeScript E2E test project."""

    def __init__(
        self,
        routes: List[Route],
        risks: Optional[List[Risk]] = None,
        output_dir: Optional[Path] = None,
        base_url: str = "http://localhost:3000",
        project_name: str = "Application",
        llm_settings: Optional[LLMSettings] = None,
        cujs: Optional[List[CUJ]] = None,
        auth_config: Optional[AuthSettings] = None,
        browsers: Optional[List[str]] = None,
        retrieval_context: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            routes=routes,
            risks=risks,
            output_dir=output_dir or Path("tests/qaagent/e2e"),
            base_url=base_url,
            project_name=project_name,
            llm_settings=llm_settings,
            retrieval_context=retrieval_context,
        )
        self.cujs = cujs or []
        self.auth_config = auth_config
        self.browsers = browsers or ["chromium"]
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_ROOT)),
            autoescape=select_autoescape(disabled_extensions=(".j2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._enhancer = None
        self._validator = TestValidator()

    def _get_enhancer(self):
        """Lazy-init LLM enhancer."""
        if self._enhancer is None and self.llm_enabled:
            from qaagent.generators.llm_enhancer import LLMTestEnhancer
            self._enhancer = LLMTestEnhancer(self.llm_settings)
        return self._enhancer

    def generate(self, **kwargs: Any) -> GenerationResult:
        """Generate complete Playwright project."""
        result = GenerationResult()
        test_count = 0

        # Create directory structure
        tests_dir = self.output_dir / "tests"
        api_tests_dir = tests_dir / "api"
        src_dir = self.output_dir / "src"
        for d in [tests_dir, api_tests_dir, src_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Separate routes
        ui_routes, api_routes = self._separate_routes()
        api_resources = self._group_api_routes(api_routes)

        # 1. package.json
        pkg_path = self._render_file(
            "playwright/package.json.j2",
            self.output_dir / "package.json",
            project_name=self.project_name,
        )
        result.files["package.json"] = pkg_path

        # 2. playwright.config.ts
        browser_devices = [
            {"name": b, "device": BROWSER_DEVICE_MAP.get(b, f"Desktop {b.capitalize()}")}
            for b in self.browsers
        ]
        config_path = self._render_file(
            "playwright/playwright.config.ts.j2",
            self.output_dir / "playwright.config.ts",
            result=result,
            base_url=self.base_url,
            browser_devices=browser_devices,
            auth_setup=self.auth_config is not None,
        )
        result.files["playwright.config.ts"] = config_path

        # 3. src/config.ts
        src_config_path = self._render_file(
            "playwright/config.ts.j2",
            src_dir / "config.ts",
            result=result,
            base_url=self.base_url,
            auth_setup=self.auth_config is not None,
        )
        result.files["src/config.ts"] = src_config_path

        # 4. auth.setup.ts (if auth configured)
        if self.auth_config:
            auth_path = self._render_file(
                "playwright/auth.setup.ts.j2",
                tests_dir / "auth.setup.ts",
                result=result,
                default_username="admin",
                default_password="password",
            )
            result.files["auth.setup.ts"] = auth_path

        # 5. Smoke tests (UI routes)
        if ui_routes:
            smoke_path = self._render_file(
                "playwright/smoke.spec.ts.j2",
                tests_dir / "smoke.spec.ts",
                result=result,
                ui_routes=ui_routes,
            )
            result.files["smoke.spec.ts"] = smoke_path
            test_count += len(ui_routes)

        # 6. API tests (grouped by resource)
        for resource_name, routes in api_resources.items():
            api_path = self._render_file(
                "playwright/api.spec.ts.j2",
                api_tests_dir / f"{resource_name}.spec.ts",
                result=result,
                resource_name=resource_name,
                routes=routes,
            )
            result.files[f"api/{resource_name}.spec.ts"] = api_path
            test_count += len(routes)

        # 7. CUJ tests
        for cuj in self.cujs:
            slug = cuj.id.replace(" ", "-").replace("_", "-").lower()
            llm_steps = self._generate_cuj_steps(cuj) if self.llm_enabled else None
            cuj_path = self._render_file(
                "playwright/cuj.spec.ts.j2",
                tests_dir / f"{slug}.spec.ts",
                result=result,
                cuj=cuj,
                llm_steps=llm_steps,
            )
            result.files[f"cuj/{slug}.spec.ts"] = cuj_path
            test_count += max(len(cuj.apis), 1)

        result.stats = {
            "tests": test_count,
            "files": len(result.files),
            "ui_routes": len(ui_routes),
            "api_routes": len(api_routes),
            "cujs": len(self.cujs),
        }
        result.llm_used = self.llm_enabled and self._enhancer is not None

        return result

    def _render_file(
        self, template_name: str, output_path: Path, result: Optional[GenerationResult] = None, **context: Any,
    ) -> Path:
        """Render a Jinja2 template to a file, validating .ts files."""
        template = self._env.get_template(template_name)
        content = template.render(**context)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        # Validate TypeScript files
        if output_path.suffix == ".ts" and result is not None:
            vr = self._validator.validate_typescript(output_path)
            if not vr.valid:
                result.warnings.append(f"{output_path.name}: {'; '.join(vr.errors)}")
            elif vr.warnings:
                result.warnings.extend(
                    f"{output_path.name}: {w}" for w in vr.warnings
                )

        return output_path

    def _separate_routes(self) -> tuple[List[Route], List[Route]]:
        """Separate routes into UI routes (GET non-/api) and API routes."""
        ui_routes: List[Route] = []
        api_routes: List[Route] = []

        for route in self.routes:
            path_lower = route.path.lower()
            if route.method.upper() == "GET" and not path_lower.startswith("/api"):
                ui_routes.append(route)
            else:
                api_routes.append(route)

        return ui_routes, api_routes

    def _group_api_routes(self, api_routes: List[Route]) -> Dict[str, List[Route]]:
        """Group API routes by resource name."""
        resources: Dict[str, List[Route]] = {}
        for route in api_routes:
            parts = [
                p for p in route.path.strip("/").split("/")
                if p and not p.startswith("{")
            ]
            # Skip the 'api' prefix if present
            if parts and parts[0].lower() == "api":
                parts = parts[1:]
            resource = parts[0] if parts else "root"
            resource = resource.replace("-", "_")
            resources.setdefault(resource, []).append(route)
        return resources

    def _generate_cuj_steps(self, cuj: CUJ) -> Optional[List[str]]:
        """Use LLM to generate meaningful test steps for a CUJ."""
        enhancer = self._get_enhancer()
        if not enhancer:
            return None

        from qaagent.llm import ChatMessage, QAAgentLLMError

        acceptance = "\n".join(f"- {a}" for a in cuj.acceptance) if cuj.acceptance else "None specified"
        apis = "\n".join(
            f"- {api.get('method', 'GET')} {api.get('path', '/')}"
            for api in cuj.apis
        ) if cuj.apis else "None specified"
        rag_text = ""
        if self.retrieval_context:
            sections = []
            for idx, snippet in enumerate(self.retrieval_context[:4], start=1):
                sections.append(f"[Snippet {idx}]\n{snippet[:1200]}")
            rag_text = "\n\nRepository context:\n" + "\n\n".join(sections)

        system = (
            "You are a QA engineer writing Playwright TypeScript E2E tests. "
            "Generate test functions for the given user journey. "
            "Return ONLY TypeScript test code (test() blocks). "
            "Use '@playwright/test' imports. Each test should be a complete `test()` call. "
            "Do NOT include describe blocks or imports."
        )
        user = (
            f"Journey: {cuj.name}\n"
            f"Components: {', '.join(cuj.components)}\n"
            f"APIs:\n{apis}\n"
            f"Acceptance criteria:\n{acceptance}\n\n"
            "Generate 2-4 meaningful test functions."
            f"{rag_text}"
        )

        try:
            messages = [
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=user),
            ]
            response = enhancer._client.chat(messages)
            content = response.content.strip()
            # Split into individual test blocks
            lines = content.splitlines()
            return lines if lines else None
        except QAAgentLLMError:
            logger.warning("LLM CUJ step generation failed, using template fallback")
            return None
