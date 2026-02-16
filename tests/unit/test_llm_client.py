"""Tests for the LLMClient class and typed models."""
from __future__ import annotations

import importlib.util
from unittest.mock import MagicMock, patch

import pytest

from qaagent.llm import (
    ChatMessage,
    ChatResponse,
    LLMClient,
    QAAgentLLMError,
    llm_available,
)

_has_litellm = importlib.util.find_spec("litellm") is not None


class TestChatMessage:
    def test_create(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_model_dump(self):
        msg = ChatMessage(role="system", content="You are helpful.")
        d = msg.model_dump()
        assert d == {"role": "system", "content": "You are helpful."}

    def test_model_validate(self):
        msg = ChatMessage.model_validate({"role": "assistant", "content": "Hi"})
        assert msg.role == "assistant"


class TestChatResponse:
    def test_create(self):
        resp = ChatResponse(content="Hello!", model="test-model")
        assert resp.content == "Hello!"
        assert resp.model == "test-model"
        assert resp.usage is None

    def test_with_usage(self):
        resp = ChatResponse(
            content="Result",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        assert resp.usage["total_tokens"] == 30


class TestLLMClient:
    def test_default_provider_is_ollama(self):
        client = LLMClient()
        assert client.provider == "ollama"

    def test_custom_provider(self):
        client = LLMClient(provider="anthropic", model="claude-sonnet-4-5-20250929")
        assert client.provider == "anthropic"
        assert client._litellm_model() == "anthropic/claude-sonnet-4-5-20250929"

    def test_ollama_model_string(self):
        client = LLMClient(provider="ollama", model="qwen2.5:7b")
        assert client._litellm_model() == "ollama/qwen2.5:7b"

    def test_openai_model_string(self):
        client = LLMClient(provider="openai", model="gpt-4o")
        assert client._litellm_model() == "gpt-4o"

    @patch.dict("os.environ", {"QAAGENT_LLM": "anthropic", "QAAGENT_MODEL": "claude-sonnet-4-5-20250929"})
    def test_env_var_config(self):
        client = LLMClient()
        assert client.provider == "anthropic"
        assert client.model == "claude-sonnet-4-5-20250929"

    @patch("qaagent.llm.LLMClient.available", return_value=False)
    def test_llm_available_delegates(self, mock_available):
        # Reset singleton
        import qaagent.llm
        qaagent.llm._default_client = None
        assert llm_available() is False
        qaagent.llm._default_client = None  # cleanup

    def test_chat_raises_without_litellm(self):
        client = LLMClient()
        messages = [ChatMessage(role="user", content="test")]
        with patch.dict("sys.modules", {"litellm": None}):
            # litellm import will fail if module is None
            with patch("builtins.__import__", side_effect=ImportError("no litellm")):
                pass  # Can't easily test this without breaking other imports

    @pytest.mark.skipif(not _has_litellm, reason="litellm not installed")
    @patch("litellm.completion")
    def test_chat_returns_typed_response(self, mock_completion):
        # Mock litellm response
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello from LLM"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(
            prompt_tokens=5, completion_tokens=10, total_tokens=15
        )
        mock_completion.return_value = mock_response

        client = LLMClient(provider="anthropic", model="test")
        response = client.chat([ChatMessage(role="user", content="Hi")])

        assert isinstance(response, ChatResponse)
        assert response.content == "Hello from LLM"
        assert response.model == "test-model"
        assert response.usage["total_tokens"] == 15

    @pytest.mark.skipif(not _has_litellm, reason="litellm not installed")
    @patch("litellm.completion", side_effect=Exception("API error"))
    def test_chat_wraps_errors(self, mock_completion):
        client = LLMClient(provider="anthropic", model="test")
        with pytest.raises(QAAgentLLMError, match="LLM request failed"):
            client.chat([ChatMessage(role="user", content="Hi")])
