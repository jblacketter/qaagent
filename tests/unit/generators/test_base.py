"""Tests for generator base infrastructure."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from qaagent.analyzers.models import Route
from qaagent.config.models import LLMSettings
from qaagent.generators.base import BaseGenerator, GenerationResult, validate_python_syntax


# -- validate_python_syntax --------------------------------------------------

class TestValidatePythonSyntax:
    def test_valid_code(self) -> None:
        valid, error = validate_python_syntax("x = 1\nprint(x)\n")
        assert valid is True
        assert error is None

    def test_valid_class(self) -> None:
        code = "class Foo:\n    def bar(self):\n        return 42\n"
        valid, error = validate_python_syntax(code)
        assert valid is True
        assert error is None

    def test_invalid_code(self) -> None:
        valid, error = validate_python_syntax("def foo(\n")
        assert valid is False
        assert error is not None
        assert "Line" in error or "unexpected" in error.lower() or "EOF" in error

    def test_syntax_error_has_line_number(self) -> None:
        code = "x = 1\ny = {\n"
        valid, error = validate_python_syntax(code)
        assert valid is False
        assert "Line" in error

    def test_empty_string_is_valid(self) -> None:
        valid, error = validate_python_syntax("")
        assert valid is True
        assert error is None

    def test_comment_only_is_valid(self) -> None:
        valid, error = validate_python_syntax("# just a comment\n")
        assert valid is True
        assert error is None


# -- GenerationResult --------------------------------------------------------

class TestGenerationResult:
    def test_defaults(self) -> None:
        result = GenerationResult()
        assert result.files == {}
        assert result.stats == {}
        assert result.warnings == []
        assert result.llm_used is False
        assert result.file_count == 0
        assert result.test_count == 0

    def test_file_count(self, tmp_path: Path) -> None:
        result = GenerationResult(
            files={"a": tmp_path / "a.py", "b": tmp_path / "b.py"},
        )
        assert result.file_count == 2

    def test_test_count(self) -> None:
        result = GenerationResult(stats={"tests": 15, "files": 3})
        assert result.test_count == 15

    def test_test_count_missing(self) -> None:
        result = GenerationResult(stats={"files": 3})
        assert result.test_count == 0

    def test_warnings(self) -> None:
        result = GenerationResult(warnings=["syntax error in foo.py"])
        assert len(result.warnings) == 1


# -- BaseGenerator -----------------------------------------------------------

def _sample_route() -> Route:
    return Route(
        path="/pets",
        method="GET",
        auth_required=False,
        responses={"200": {"description": "OK"}},
    )


class ConcreteGenerator(BaseGenerator):
    """Minimal concrete implementation for testing."""

    def generate(self, **kwargs: Any) -> GenerationResult:
        return GenerationResult(
            files={"test": self.output_dir / "test.py"},
            stats={"tests": len(self.routes)},
            llm_used=self.llm_enabled,
        )


class TestBaseGenerator:
    def test_init_defaults(self) -> None:
        gen = ConcreteGenerator(routes=[_sample_route()])
        assert gen.base_url == "http://localhost:8000"
        assert gen.project_name == "Application"
        assert gen.risks == []
        assert gen.llm_enabled is False

    def test_init_with_llm(self) -> None:
        settings = LLMSettings(enabled=True, provider="ollama", model="test")
        gen = ConcreteGenerator(routes=[_sample_route()], llm_settings=settings)
        assert gen.llm_enabled is True

    def test_init_with_disabled_llm(self) -> None:
        settings = LLMSettings(enabled=False)
        gen = ConcreteGenerator(routes=[_sample_route()], llm_settings=settings)
        assert gen.llm_enabled is False

    def test_generate_returns_result(self) -> None:
        gen = ConcreteGenerator(routes=[_sample_route(), _sample_route()])
        result = gen.generate()
        assert isinstance(result, GenerationResult)
        assert result.stats["tests"] == 2
