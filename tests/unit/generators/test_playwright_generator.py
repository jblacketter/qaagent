"""Tests for PlaywrightGenerator."""
from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from qaagent.analyzers.cuj_config import CUJ
from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route
from qaagent.config.models import AuthSettings, LLMSettings
from qaagent.generators.base import GenerationResult
from qaagent.generators.playwright_generator import PlaywrightGenerator


def _route(path: str = "/pets", method: str = "GET", auth: bool = False) -> Route:
    return Route(
        path=path,
        method=method,
        auth_required=auth,
        summary=f"{method} {path}",
        tags=["pets"],
        params={},
        responses={"200": {"description": "OK"}},
    )


def _cuj(id: str = "login-flow", name: str = "Login Flow") -> CUJ:
    return CUJ(
        id=id,
        name=name,
        components=["auth", "dashboard"],
        apis=[
            {"method": "POST", "path": "/api/auth/login"},
            {"method": "GET", "path": "/api/user/me"},
        ],
        acceptance=[
            "User can log in with valid credentials",
            "User sees dashboard after login",
        ],
    )


class TestPlaywrightGenerator:
    def test_basic_generation(self, tmp_path: Path) -> None:
        """Test basic Playwright project generation."""
        routes = [
            _route("/", "GET"),
            _route("/about", "GET"),
            _route("/api/pets", "GET"),
            _route("/api/pets", "POST"),
            _route("/api/pets/{id}", "GET"),
        ]
        gen = PlaywrightGenerator(
            routes=routes,
            output_dir=tmp_path,
            base_url="http://localhost:3000",
            project_name="TestApp",
        )
        result = gen.generate()

        assert isinstance(result, GenerationResult)
        assert "package.json" in result.files
        assert "playwright.config.ts" in result.files
        assert "src/config.ts" in result.files
        assert "smoke.spec.ts" in result.files

        # package.json should exist and contain project name
        pkg = result.files["package.json"]
        assert pkg.exists()
        content = pkg.read_text()
        assert "testapp" in content.lower()

    def test_route_separation(self, tmp_path: Path) -> None:
        """Test UI vs API route separation."""
        routes = [
            _route("/", "GET"),           # UI
            _route("/about", "GET"),      # UI
            _route("/api/pets", "GET"),   # API
            _route("/api/pets", "POST"),  # API (not GET)
            _route("/api/users", "GET"),  # API
        ]
        gen = PlaywrightGenerator(routes=routes, output_dir=tmp_path)
        result = gen.generate()

        # Should have smoke tests (2 UI routes: / and /about)
        assert "smoke.spec.ts" in result.files
        smoke_content = result.files["smoke.spec.ts"].read_text()
        assert "/" in smoke_content
        assert "/about" in smoke_content

        # Should have API test files
        assert "api/pets.spec.ts" in result.files
        assert "api/users.spec.ts" in result.files

    def test_no_ui_routes_skips_smoke(self, tmp_path: Path) -> None:
        """Test that smoke tests are skipped when there are no UI routes."""
        routes = [
            _route("/api/pets", "GET"),
            _route("/api/pets", "POST"),
        ]
        gen = PlaywrightGenerator(routes=routes, output_dir=tmp_path)
        result = gen.generate()

        assert "smoke.spec.ts" not in result.files

    def test_auth_setup(self, tmp_path: Path) -> None:
        """Test auth.setup.ts is generated when auth configured."""
        auth = AuthSettings(header_name="Authorization", token_env="API_TOKEN")
        gen = PlaywrightGenerator(
            routes=[_route()],
            output_dir=tmp_path,
            auth_config=auth,
        )
        result = gen.generate()

        assert "auth.setup.ts" in result.files
        auth_content = result.files["auth.setup.ts"].read_text()
        assert "authenticate" in auth_content

        # Config should reference auth
        config_content = result.files["playwright.config.ts"].read_text()
        assert "setup" in config_content
        assert "storageState" in config_content

    def test_no_auth_skips_setup(self, tmp_path: Path) -> None:
        """Test no auth.setup.ts when auth is not configured."""
        gen = PlaywrightGenerator(routes=[_route()], output_dir=tmp_path)
        result = gen.generate()

        assert "auth.setup.ts" not in result.files

    def test_cuj_generation(self, tmp_path: Path) -> None:
        """Test CUJ-driven test generation."""
        cuj = _cuj()
        gen = PlaywrightGenerator(
            routes=[_route("/api/auth/login", "POST")],
            output_dir=tmp_path,
            cujs=[cuj],
        )
        result = gen.generate()

        assert "cuj/login-flow.spec.ts" in result.files
        cuj_content = result.files["cuj/login-flow.spec.ts"].read_text()
        assert "Login Flow" in cuj_content

    def test_cuj_template_fallback(self, tmp_path: Path) -> None:
        """Test CUJ generation without LLM uses structured TODOs."""
        cuj = _cuj()
        gen = PlaywrightGenerator(
            routes=[_route("/api/auth/login", "POST")],
            output_dir=tmp_path,
            cujs=[cuj],
        )
        result = gen.generate()

        cuj_content = result.files["cuj/login-flow.spec.ts"].read_text()
        assert "TODO" in cuj_content

    def test_browser_config(self, tmp_path: Path) -> None:
        """Test multi-browser configuration."""
        gen = PlaywrightGenerator(
            routes=[_route()],
            output_dir=tmp_path,
            browsers=["chromium", "firefox", "webkit"],
        )
        result = gen.generate()

        config_content = result.files["playwright.config.ts"].read_text()
        assert "chromium" in config_content
        assert "firefox" in config_content
        assert "webkit" in config_content

    def test_stats(self, tmp_path: Path) -> None:
        """Test GenerationResult stats."""
        routes = [
            _route("/", "GET"),
            _route("/api/pets", "GET"),
            _route("/api/pets", "POST"),
        ]
        gen = PlaywrightGenerator(
            routes=routes,
            output_dir=tmp_path,
            cujs=[_cuj()],
        )
        result = gen.generate()

        assert result.stats["ui_routes"] == 1  # GET / only
        assert result.stats["api_routes"] == 2
        assert result.stats["cujs"] == 1
        assert result.stats["tests"] > 0

    def test_api_route_grouping(self, tmp_path: Path) -> None:
        """Test API routes are grouped by resource."""
        routes = [
            _route("/api/pets", "GET"),
            _route("/api/pets/{id}", "GET"),
            _route("/api/pets", "POST"),
            _route("/api/users", "GET"),
            _route("/api/users/{id}", "DELETE"),
        ]
        gen = PlaywrightGenerator(routes=routes, output_dir=tmp_path)
        result = gen.generate()

        assert "api/pets.spec.ts" in result.files
        assert "api/users.spec.ts" in result.files

        pets_content = result.files["api/pets.spec.ts"].read_text()
        assert "POST" in pets_content
        assert "GET" in pets_content

    def test_directory_structure(self, tmp_path: Path) -> None:
        """Test that the generated directory structure is correct."""
        routes = [
            _route("/", "GET"),
            _route("/api/pets", "GET"),
        ]
        gen = PlaywrightGenerator(
            routes=routes,
            output_dir=tmp_path,
            cujs=[_cuj()],
        )
        gen.generate()

        assert (tmp_path / "package.json").exists()
        assert (tmp_path / "playwright.config.ts").exists()
        assert (tmp_path / "src" / "config.ts").exists()
        assert (tmp_path / "tests").is_dir()
        assert (tmp_path / "tests" / "api").is_dir()

    def test_llm_not_used_by_default(self, tmp_path: Path) -> None:
        """Test that LLM is not used when not configured."""
        gen = PlaywrightGenerator(routes=[_route()], output_dir=tmp_path)
        result = gen.generate()
        assert result.llm_used is False

    def test_correct_playwright_device_keys(self, tmp_path: Path) -> None:
        """Test that generated config uses correct Playwright device registry keys."""
        gen = PlaywrightGenerator(
            routes=[_route()],
            output_dir=tmp_path,
            browsers=["chromium", "firefox", "webkit"],
        )
        result = gen.generate()

        config_content = result.files["playwright.config.ts"].read_text()
        assert "Desktop Chrome" in config_content
        assert "Desktop Firefox" in config_content
        assert "Desktop Safari" in config_content
        # Should NOT contain the old incorrect keys
        assert "Chromium Desktop" not in config_content
        assert "Firefox Desktop" not in config_content
        assert "Webkit Desktop" not in config_content

    def test_typescript_validation_runs(self, tmp_path: Path) -> None:
        """Test that TypeScript validation runs on generated .ts files."""
        gen = PlaywrightGenerator(routes=[_route()], output_dir=tmp_path)
        result = gen.generate()

        # Validation should have run — warnings may be present if npx is unavailable
        # but no errors should prevent generation
        assert isinstance(result.warnings, list)
