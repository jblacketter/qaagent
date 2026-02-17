"""Contract tests for the Agent API endpoints (Phase 20)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from qaagent.api.routes.repositories import Repository, repositories
from qaagent.api.routes.agent import _configs, _usage, _AgentConfig, _UsageAccumulator, _mask_key, _estimate_cost
from qaagent.doc.generator import save_documentation
from qaagent.doc.models import AppDocumentation


@pytest.fixture(autouse=True)
def _clear_stores():
    """Clear in-memory repositories, configs, and usage before/after each test."""
    repositories.clear()
    _configs.clear()
    _usage.clear()
    yield
    repositories.clear()
    _configs.clear()
    _usage.clear()


@pytest.fixture()
def client():
    """Test client for the web_ui app (has all routers mounted)."""
    from qaagent.web_ui import app
    return TestClient(app)


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Repository:
    """Register a sample repo with pre-generated documentation."""
    repo = Repository(
        id="test-repo",
        name="test-repo",
        path=str(tmp_path),
        repo_type="local",
        analysis_options={"testCoverage": True},
    )
    repositories["test-repo"] = repo

    doc = AppDocumentation(
        app_name="test-repo",
        generated_at="2026-01-01T00:00:00",
        content_hash="abc123",
        source_dir=str(tmp_path),
        features=[],
        integrations=[],
        total_routes=5,
    )
    save_documentation(doc, tmp_path)
    return repo


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestMaskKey:
    def test_masks_long_key(self):
        assert _mask_key("sk-123456789abcdef") == "sk-1***cdef"

    def test_short_key_fully_masked(self):
        assert _mask_key("short") == "***"

    def test_exactly_eight_chars(self):
        assert _mask_key("12345678") == "***"

    def test_nine_chars_shows_edges(self):
        assert _mask_key("123456789") == "1234***6789"


class TestEstimateCost:
    def test_known_model_cost(self):
        # claude-sonnet-4-5-20250929: $3/M input, $15/M output
        cost = _estimate_cost("claude-sonnet-4-5-20250929", 1_000_000, 1_000_000)
        assert cost == 18.0  # 3 + 15

    def test_unknown_model_zero(self):
        assert _estimate_cost("unknown-model", 100_000, 100_000) == 0.0

    def test_prefix_match(self):
        cost = _estimate_cost("claude-sonnet-4-5", 1_000_000, 0)
        assert cost == 3.0


# ---------------------------------------------------------------------------
# Config CRUD endpoints
# ---------------------------------------------------------------------------


class TestAgentConfigEndpoints:
    def test_save_config(self, client: TestClient, sample_repo: Repository):
        """POST /api/agent/config saves config and returns masked key."""
        response = client.post(
            "/api/agent/config",
            params={"repo_id": "test-repo"},
            json={"provider": "anthropic", "model": "claude-sonnet-4-5-20250929", "api_key": "sk-test1234abcd5678"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-sonnet-4-5-20250929"
        # Key is masked
        assert "sk-t" in data["api_key_masked"]
        assert "5678" in data["api_key_masked"]
        assert "***" in data["api_key_masked"]
        # Raw key is NOT in response
        assert "sk-test1234abcd5678" not in str(data)

    def test_get_config_returns_masked_key(self, client: TestClient, sample_repo: Repository):
        """GET /api/agent/config returns masked key, never raw."""
        _configs["test-repo"] = _AgentConfig(
            provider="openai", model="gpt-4o", api_key="sk-secret1234secret"
        )
        response = client.get("/api/agent/config", params={"repo_id": "test-repo"})
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o"
        assert "***" in data["api_key_masked"]
        # Ensure raw key never appears
        assert "sk-secret1234secret" not in str(data)

    def test_get_config_unconfigured(self, client: TestClient, sample_repo: Repository):
        """GET /api/agent/config with no saved config and no env var returns defaults."""
        with patch.dict("os.environ", {}, clear=False):
            # Remove env var if present
            import os
            env_backup = os.environ.pop("ANTHROPIC_API_KEY", None)
            try:
                response = client.get("/api/agent/config", params={"repo_id": "test-repo"})
                assert response.status_code == 200
                data = response.json()
                assert data["configured"] is False
                assert data["api_key_masked"] == ""
            finally:
                if env_backup is not None:
                    os.environ["ANTHROPIC_API_KEY"] = env_backup

    def test_delete_config(self, client: TestClient, sample_repo: Repository):
        """DELETE /api/agent/config removes config."""
        _configs["test-repo"] = _AgentConfig(api_key="sk-toberemoved12345678")
        response = client.delete("/api/agent/config", params={"repo_id": "test-repo"})
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        assert "test-repo" not in _configs


# ---------------------------------------------------------------------------
# Error boundary tests (repo_id validation)
# ---------------------------------------------------------------------------


class TestAgentRepoValidation:
    def test_missing_repo_id_returns_400(self, client: TestClient):
        """All agent endpoints require repo_id — omitting it → 400."""
        assert client.get("/api/agent/config").status_code == 400
        assert client.post("/api/agent/config", json={"provider": "anthropic", "model": "m", "api_key": "k"}).status_code == 400
        assert client.delete("/api/agent/config").status_code == 400
        assert client.post("/api/agent/analyze").status_code == 400
        assert client.get("/api/agent/usage").status_code == 400
        assert client.delete("/api/agent/usage").status_code == 400

    def test_unknown_repo_id_returns_404(self, client: TestClient):
        """Agent endpoints with non-existent repo_id → 404."""
        assert client.get("/api/agent/config", params={"repo_id": "ghost"}).status_code == 404
        assert client.post("/api/agent/analyze", params={"repo_id": "ghost"}).status_code == 404
        assert client.get("/api/agent/usage", params={"repo_id": "ghost"}).status_code == 404


# ---------------------------------------------------------------------------
# Analyze endpoint (LLM mocked)
# ---------------------------------------------------------------------------


class TestAnalyzeEndpoint:
    def test_analyze_no_config_returns_400(self, client: TestClient, sample_repo: Repository):
        """POST /api/agent/analyze without config and no env var → 400."""
        import os
        env_backup = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            response = client.post("/api/agent/analyze", params={"repo_id": "test-repo"})
            assert response.status_code == 400
            assert "not configured" in response.json()["detail"].lower()
        finally:
            if env_backup is not None:
                os.environ["ANTHROPIC_API_KEY"] = env_backup

    def test_analyze_success_with_mocked_llm(self, client: TestClient, sample_repo: Repository):
        """POST /api/agent/analyze with mocked LLM returns content and accumulates usage."""
        _configs["test-repo"] = _AgentConfig(
            provider="anthropic", model="claude-sonnet-4-5-20250929", api_key="sk-test1234abcd5678"
        )

        mock_response = MagicMock()
        mock_response.content = "# Enhanced Documentation\n\nGreat app."
        mock_response.model = "claude-sonnet-4-5-20250929"
        mock_response.usage = {
            "prompt_tokens": 500,
            "completion_tokens": 200,
            "total_tokens": 700,
        }

        with patch("qaagent.llm.LLMClient") as MockClient:
            MockClient.return_value.chat.return_value = mock_response
            response = client.post("/api/agent/analyze", params={"repo_id": "test-repo"})

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "# Enhanced Documentation\n\nGreat app."
        assert data["model"] == "claude-sonnet-4-5-20250929"

        # Usage was accumulated
        assert "test-repo" in _usage
        assert _usage["test-repo"].requests == 1
        assert _usage["test-repo"].prompt_tokens == 500
        assert _usage["test-repo"].completion_tokens == 200
        assert _usage["test-repo"].total_tokens == 700

    def test_analyze_llm_error_returns_502(self, client: TestClient, sample_repo: Repository):
        """POST /api/agent/analyze when LLM fails → 502 and request still counted."""
        _configs["test-repo"] = _AgentConfig(
            provider="anthropic", model="claude-sonnet-4-5-20250929", api_key="sk-test1234abcd5678"
        )

        from qaagent.llm import QAAgentLLMError

        with patch("qaagent.llm.LLMClient") as MockClient:
            MockClient.return_value.chat.side_effect = QAAgentLLMError("timeout")
            response = client.post("/api/agent/analyze", params={"repo_id": "test-repo"})

        assert response.status_code == 502
        assert "timeout" in response.json()["detail"]
        # Request counted even on failure
        assert _usage["test-repo"].requests == 1

    def test_analyze_no_documentation_returns_404(self, client: TestClient):
        """POST /api/agent/analyze when repo has no documentation → 404."""
        repo = Repository(
            id="empty-repo", name="empty-repo", path="/tmp/empty",
            repo_type="local", analysis_options={},
        )
        repositories["empty-repo"] = repo
        _configs["empty-repo"] = _AgentConfig(api_key="sk-test1234abcd5678")

        with patch("qaagent.doc.generator.load_documentation", return_value=None):
            response = client.post("/api/agent/analyze", params={"repo_id": "empty-repo"})
        assert response.status_code == 404
        assert "No documentation found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Usage endpoints
# ---------------------------------------------------------------------------


class TestUsageEndpoints:
    def test_get_usage_empty(self, client: TestClient, sample_repo: Repository):
        """GET /api/agent/usage with no usage → zeroes."""
        response = client.get("/api/agent/usage", params={"repo_id": "test-repo"})
        assert response.status_code == 200
        data = response.json()
        assert data["repo_id"] == "test-repo"
        assert data["requests"] == 0
        assert data["prompt_tokens"] == 0
        assert data["estimated_cost_usd"] == 0.0

    def test_get_usage_accumulated(self, client: TestClient, sample_repo: Repository):
        """GET /api/agent/usage returns accumulated stats."""
        _configs["test-repo"] = _AgentConfig(model="claude-sonnet-4-5-20250929", api_key="k")
        acc = _UsageAccumulator()
        acc.add({"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500})
        acc.add({"prompt_tokens": 2000, "completion_tokens": 1000, "total_tokens": 3000})
        _usage["test-repo"] = acc

        response = client.get("/api/agent/usage", params={"repo_id": "test-repo"})
        assert response.status_code == 200
        data = response.json()
        assert data["requests"] == 2
        assert data["prompt_tokens"] == 3000
        assert data["completion_tokens"] == 1500
        assert data["total_tokens"] == 4500
        assert data["estimated_cost_usd"] > 0

    def test_reset_usage(self, client: TestClient, sample_repo: Repository):
        """DELETE /api/agent/usage resets counters."""
        _usage["test-repo"] = _UsageAccumulator(requests=5, prompt_tokens=10000)
        response = client.delete("/api/agent/usage", params={"repo_id": "test-repo"})
        assert response.status_code == 200
        assert response.json()["status"] == "reset"
        assert "test-repo" not in _usage

    def test_usage_keyed_by_repo_id(self, client: TestClient):
        """Usage is keyed by repo_id — separate repos have independent counters."""
        repo_a = Repository(id="repo-a", name="a", path="/tmp/a", repo_type="local", analysis_options={})
        repo_b = Repository(id="repo-b", name="b", path="/tmp/b", repo_type="local", analysis_options={})
        repositories["repo-a"] = repo_a
        repositories["repo-b"] = repo_b

        _configs["repo-a"] = _AgentConfig(model="gpt-4o", api_key="k")
        acc_a = _UsageAccumulator()
        acc_a.add({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
        _usage["repo-a"] = acc_a

        resp_a = client.get("/api/agent/usage", params={"repo_id": "repo-a"})
        resp_b = client.get("/api/agent/usage", params={"repo_id": "repo-b"})

        assert resp_a.json()["requests"] == 1
        assert resp_b.json()["requests"] == 0


# ---------------------------------------------------------------------------
# Agent analysis persistence
# ---------------------------------------------------------------------------


class TestAgentAnalysisPersistence:
    def test_analyze_auto_saves_agent_analysis(self, client: TestClient, sample_repo: Repository, tmp_path: Path):
        """POST /api/agent/analyze auto-saves agent_analysis into appdoc.json."""
        _configs["test-repo"] = _AgentConfig(
            provider="anthropic", model="claude-sonnet-4-5-20250929", api_key="sk-test1234abcd5678"
        )

        mock_response = MagicMock()
        mock_response.content = "# AI Enhanced\n\nPersisted content."
        mock_response.model = "claude-sonnet-4-5-20250929"
        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        with patch("qaagent.llm.LLMClient") as MockClient:
            MockClient.return_value.chat.return_value = mock_response
            response = client.post("/api/agent/analyze", params={"repo_id": "test-repo"})

        assert response.status_code == 200

        # Verify it was persisted to disk
        from qaagent.doc.generator import load_documentation
        doc = load_documentation(tmp_path)
        assert doc is not None
        assert doc.agent_analysis is not None
        assert doc.agent_analysis.enhanced_markdown == "# AI Enhanced\n\nPersisted content."
        assert doc.agent_analysis.model_used == "claude-sonnet-4-5-20250929"
        assert doc.agent_analysis.generated_at != ""

    def test_app_doc_get_includes_agent_analysis(self, client: TestClient, sample_repo: Repository, tmp_path: Path):
        """GET /api/doc returns agent_analysis after it has been saved."""
        from qaagent.doc.models import AgentAnalysis
        from qaagent.doc.generator import load_documentation

        # Load existing doc, add agent_analysis, re-save
        doc = load_documentation(tmp_path)
        assert doc is not None
        doc.agent_analysis = AgentAnalysis(
            enhanced_markdown="# Saved Analysis",
            model_used="test-model",
            generated_at="2026-02-16T12:00:00",
        )
        save_documentation(doc, tmp_path)

        response = client.get("/api/doc", params={"repo_id": "test-repo"})
        assert response.status_code == 200
        data = response.json()
        assert data["agent_analysis"] is not None
        assert data["agent_analysis"]["enhanced_markdown"] == "# Saved Analysis"
        assert data["agent_analysis"]["model_used"] == "test-model"


# ---------------------------------------------------------------------------
# Env-var fallback for API key
# ---------------------------------------------------------------------------


class TestEnvVarFallback:
    def test_env_var_fallback_shows_configured(self, client: TestClient, sample_repo: Repository):
        """GET /api/agent/config with ANTHROPIC_API_KEY env var shows configured."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-envvar1234567890"}):
            response = client.get("/api/agent/config", params={"repo_id": "test-repo"})

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert "***" in data["api_key_masked"]

    def test_env_var_fallback_enables_analyze(self, client: TestClient, sample_repo: Repository):
        """POST /api/agent/analyze succeeds with env-var API key (no explicit config)."""
        mock_response = MagicMock()
        mock_response.content = "# From env key"
        mock_response.model = "claude-sonnet-4-5-20250929"
        mock_response.usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-envvar1234567890"}):
            with patch("qaagent.llm.LLMClient") as MockClient:
                MockClient.return_value.chat.return_value = mock_response
                response = client.post("/api/agent/analyze", params={"repo_id": "test-repo"})

        assert response.status_code == 200
        assert response.json()["content"] == "# From env key"

    def test_explicit_config_overrides_env_var(self, client: TestClient, sample_repo: Repository):
        """Explicit config takes precedence over ANTHROPIC_API_KEY env var."""
        _configs["test-repo"] = _AgentConfig(
            provider="openai", model="gpt-4o", api_key="sk-explicit12345678"
        )

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-envvar1234567890"}):
            response = client.get("/api/agent/config", params={"repo_id": "test-repo"})

        data = response.json()
        assert data["configured"] is True
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o"
