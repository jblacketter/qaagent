"""Tests for LLMTestEnhancer with mocked LLMClient."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import json

import pytest

from qaagent.analyzers.models import Risk, RiskCategory, RiskSeverity, Route
from qaagent.config.models import LLMSettings
from qaagent.generators.llm_enhancer import LLMTestEnhancer
from qaagent.llm import ChatResponse, QAAgentLLMError


def _settings() -> LLMSettings:
    return LLMSettings(enabled=True, provider="ollama", model="test-model")


def _route(path: str = "/pets", method: str = "GET") -> Route:
    return Route(
        path=path,
        method=method,
        auth_required=False,
        params={"pet_id": {"type": "integer"}},
        responses={"200": {"description": "OK"}},
    )


def _risk() -> Risk:
    return Risk(
        category=RiskCategory.SECURITY,
        severity=RiskSeverity.HIGH,
        route="POST /pets",
        title="No auth on mutation",
        description="POST endpoint lacks authentication",
        recommendation="Add auth middleware",
    )


class TestEnhanceAssertions:
    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_returns_assertion_lines(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(
            content="assert response.status_code == 200\nassert 'name' in response.json()\nassert response.headers['content-type'] == 'application/json'"
        )
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        assertions = enhancer.enhance_assertions(_route())

        assert len(assertions) == 3
        assert all(a.startswith("assert") for a in assertions)

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_filters_non_assert_lines(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(
            content="# Some comment\nassert response.status_code == 200\nprint('debug')\nassert 'id' in response.json()"
        )
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        assertions = enhancer.enhance_assertions(_route())

        assert len(assertions) == 2
        assert all(a.startswith("assert") for a in assertions)

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_fallback_on_llm_error(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.side_effect = QAAgentLLMError("connection refused")
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        assertions = enhancer.enhance_assertions(_route())

        assert len(assertions) >= 1
        assert any("status_code" in a for a in assertions)

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_includes_retrieval_context_in_prompt(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(content="assert response.status_code == 200")
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        enhancer.enhance_assertions(_route(), retrieval_context=["src/pets.py:1-3\nvalidate name"])

        sent_messages = mock_client.chat.call_args.args[0]
        assert "Repository context" in sent_messages[1].content
        assert "src/pets.py" in sent_messages[1].content


class TestGenerateEdgeCases:
    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_returns_edge_cases(self, mock_cls) -> None:
        cases = [
            {"name": "negative_id", "params": {"id": -1}, "expected_status": 404, "description": "Negative ID"},
            {"name": "zero_id", "params": {"id": 0}, "expected_status": 404, "description": "Zero ID"},
        ]
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(content=json.dumps(cases))
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        result = enhancer.generate_edge_cases(_route(), [_risk()])

        assert len(result) == 2
        assert result[0]["name"] == "negative_id"

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_strips_markdown_fences(self, mock_cls) -> None:
        cases = [{"name": "test", "params": {}, "expected_status": 400, "description": "Test"}]
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(
            content=f"```json\n{json.dumps(cases)}\n```"
        )
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        result = enhancer.generate_edge_cases(_route(), [])

        assert len(result) == 1

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_fallback_on_invalid_json(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(content="not valid json")
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        result = enhancer.generate_edge_cases(_route(), [])

        # Should return fallback edge cases
        assert len(result) >= 1
        assert all("name" in c for c in result)


class TestGenerateTestBody:
    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_returns_body_code(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(
            content='    response = client.get(base_url + "/pets")\n    assert response.status_code == 200'
        )
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        body = enhancer.generate_test_body(_route())

        assert "response" in body
        assert "client" in body

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_fallback_on_error(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.side_effect = QAAgentLLMError("timeout")
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        body = enhancer.generate_test_body(_route())

        assert "response" in body or "client" in body


class TestRefineCode:
    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_returns_fixed_code(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(content="x = 1\nprint(x)\n")
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        fixed = enhancer.refine_code("x = 1\nprint(x", "unexpected EOF")

        assert "print(x)" in fixed

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_strips_markdown_fences(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(content="```python\nx = 1\n```")
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        fixed = enhancer.refine_code("x = ", "syntax error")

        assert "```" not in fixed
        assert "x = 1" in fixed

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_returns_original_on_error(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.side_effect = QAAgentLLMError("fail")
        mock_cls.return_value = mock_client

        original = "x = "
        enhancer = LLMTestEnhancer(_settings())
        result = enhancer.refine_code(original, "syntax error")

        assert result == original


class TestGenerateStepDefinitions:
    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_returns_step_lines(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(
            content="the response status should be 401\nthe response body should contain an error message"
        )
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        steps = enhancer.generate_step_definitions(_route(), _risk())

        assert len(steps) == 2
        assert any("401" in s for s in steps)

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_fallback_on_error(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.side_effect = QAAgentLLMError("fail")
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        steps = enhancer.generate_step_definitions(_route())

        assert len(steps) >= 1


class TestGenerateResponseAssertions:
    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_returns_assertion_steps(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = ChatResponse(
            content="the response should contain a list of items\nthe response should have valid JSON format"
        )
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        steps = enhancer.generate_response_assertions(_route())

        assert len(steps) == 2

    @patch("qaagent.generators.llm_enhancer.LLMClient")
    def test_fallback_on_error(self, mock_cls) -> None:
        mock_client = MagicMock()
        mock_client.chat.side_effect = QAAgentLLMError("fail")
        mock_cls.return_value = mock_client

        enhancer = LLMTestEnhancer(_settings())
        steps = enhancer.generate_response_assertions(_route())

        assert len(steps) >= 1
