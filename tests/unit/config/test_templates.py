"""Tests for config/templates.py — Jinja2 config template rendering."""
from __future__ import annotations

import pytest

from qaagent.config.templates import (
    TemplateContext,
    available_templates,
    render_template,
)


class TestTemplateContext:
    def test_required_fields(self):
        ctx = TemplateContext(
            project_name="myapp",
            project_type="fastapi",
            base_url="http://localhost:8765",
        )
        assert ctx.project_name == "myapp"
        assert ctx.health_endpoint == "/health"  # default

    def test_all_fields(self):
        ctx = TemplateContext(
            project_name="myapp",
            project_type="nextjs",
            base_url="http://localhost:3000",
            start_command="npm run dev",
            health_endpoint="/api/health",
            spec_path="openapi.yaml",
            source_dir="src/app/api",
        )
        assert ctx.source_dir == "src/app/api"


class TestAvailableTemplates:
    def test_returns_dict(self):
        templates = available_templates()
        assert isinstance(templates, dict)

    def test_includes_known_templates(self):
        templates = available_templates()
        assert "fastapi" in templates
        assert "nextjs" in templates
        assert "generic" in templates


class TestRenderTemplate:
    def test_render_fastapi(self):
        ctx = TemplateContext(
            project_name="petstore",
            project_type="fastapi",
            base_url="http://localhost:8765",
        )
        output = render_template("fastapi", ctx)

        assert "petstore" in output or "8765" in output
        assert isinstance(output, str)
        assert len(output) > 0

    def test_render_nextjs(self):
        ctx = TemplateContext(
            project_name="mysite",
            project_type="nextjs",
            base_url="http://localhost:3000",
            source_dir="src/app/api",
        )
        output = render_template("nextjs", ctx)

        assert isinstance(output, str)
        assert len(output) > 0

    def test_render_generic(self):
        ctx = TemplateContext(
            project_name="myapp",
            project_type="generic",
            base_url="http://localhost:8000",
        )
        output = render_template("generic", ctx)

        assert isinstance(output, str)
        assert len(output) > 0

    def test_unknown_template_raises(self):
        ctx = TemplateContext(
            project_name="myapp",
            project_type="generic",
            base_url="http://localhost:8000",
        )
        with pytest.raises(ValueError, match="Unknown template"):
            render_template("nonexistent_template", ctx)
