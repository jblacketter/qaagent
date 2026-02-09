"""Tests for TestValidator."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qaagent.config.models import LLMSettings
from qaagent.generators.validator import TestValidator, ValidationResult
from qaagent.llm import ChatResponse, QAAgentLLMError


@pytest.fixture
def validator() -> TestValidator:
    return TestValidator()


class TestValidatePython:
    def test_valid_code(self, validator: TestValidator) -> None:
        result = validator.validate_python("x = 1\nprint(x)\n")
        assert result.valid is True
        assert result.language == "python"
        assert result.errors == []

    def test_invalid_code(self, validator: TestValidator) -> None:
        result = validator.validate_python("def foo(\n")
        assert result.valid is False
        assert result.language == "python"
        assert len(result.errors) > 0

    def test_empty_string(self, validator: TestValidator) -> None:
        result = validator.validate_python("")
        assert result.valid is True

    def test_class_definition(self, validator: TestValidator) -> None:
        code = "class Foo:\n    pass\n"
        result = validator.validate_python(code)
        assert result.valid is True


class TestValidateGherkin:
    def test_valid_feature(self, validator: TestValidator) -> None:
        text = """Feature: Pets API
  Scenario: List pets
    Given I have API access
    When I send a GET to /pets
    Then the response status should be 200
"""
        result = validator.validate_gherkin(text)
        assert result.valid is True
        assert result.language == "gherkin"

    def test_missing_feature(self, validator: TestValidator) -> None:
        text = """Scenario: List pets
    Given I have API access
"""
        result = validator.validate_gherkin(text)
        assert result.valid is False
        assert any("Feature" in e for e in result.errors)

    def test_missing_scenario(self, validator: TestValidator) -> None:
        text = """Feature: Pets API
    Some description
"""
        result = validator.validate_gherkin(text)
        assert result.valid is False
        assert any("Scenario" in e for e in result.errors)

    def test_empty_file(self, validator: TestValidator) -> None:
        result = validator.validate_gherkin("")
        assert result.valid is False

    def test_scenario_outline(self, validator: TestValidator) -> None:
        text = """Feature: Pets API
  Scenario Outline: Test <method> on /pets
    Given I have API access
"""
        result = validator.validate_gherkin(text)
        assert result.valid is True


class TestValidateTypeScript:
    def test_skips_when_npx_not_found(self, validator: TestValidator) -> None:
        with patch("qaagent.generators.validator.shutil.which", return_value=None):
            result = validator.validate_typescript(Path("/tmp/test.ts"))
            assert result.valid is True
            assert result.language == "typescript"
            assert any("npx not found" in w for w in result.warnings)


class TestValidateAndFix:
    def test_valid_code_not_fixed(self, validator: TestValidator) -> None:
        code = "x = 1\n"
        result_code, was_fixed = validator.validate_and_fix(code, "python")
        assert result_code == code
        assert was_fixed is False

    def test_invalid_code_no_enhancer(self, validator: TestValidator) -> None:
        code = "def foo(\n"
        result_code, was_fixed = validator.validate_and_fix(code, "python")
        assert was_fixed is False

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_invalid_code_with_enhancer_fix(self, mock_cls, validator: TestValidator) -> None:
        from qaagent.generators.llm_enhancer import LLMTestEnhancer

        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(content="def foo():\n    pass\n")
        mock_cls.return_value = mock_client

        settings = LLMSettings(enabled=True, provider="ollama", model="test")
        enhancer = LLMTestEnhancer(settings)

        code = "def foo(\n"
        result_code, was_fixed = validator.validate_and_fix(code, "python", enhancer=enhancer)
        assert was_fixed is True
        assert "def foo():" in result_code

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_unfixable_code(self, mock_cls, validator: TestValidator) -> None:
        from qaagent.generators.llm_enhancer import LLMTestEnhancer

        mock_client = MagicMock()
        # LLM returns still-broken code
        mock_client.chat.return_value = ChatResponse(content="still broken(\n")
        mock_cls.return_value = mock_client

        settings = LLMSettings(enabled=True, provider="ollama", model="test")
        enhancer = LLMTestEnhancer(settings)

        code = "def foo(\n"
        result_code, was_fixed = validator.validate_and_fix(code, "python", enhancer=enhancer)
        assert was_fixed is False

    def test_gherkin_validation_and_fix(self, validator: TestValidator) -> None:
        valid_gherkin = "Feature: Test\n  Scenario: Test\n"
        result_code, was_fixed = validator.validate_and_fix(valid_gherkin, "gherkin")
        assert was_fixed is False

    def test_typescript_passthrough(self, validator: TestValidator) -> None:
        code = "const x: string = 'hello';"
        result_code, was_fixed = validator.validate_and_fix(code, "typescript")
        assert result_code == code
        assert was_fixed is False


class TestValidationResult:
    def test_defaults(self) -> None:
        result = ValidationResult(valid=True, language="python")
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_with_errors(self) -> None:
        result = ValidationResult(valid=False, language="python", errors=["syntax error"])
        assert result.valid is False
        assert len(result.errors) == 1
