"""Tests for config/legacy.py — legacy TOML config loading."""
from __future__ import annotations

from pathlib import Path

from qaagent.config.legacy import (
    APIAuth,
    APIConfig,
    LegacyQAAgentConfig,
    load_config,
    write_default_config,
    write_env_example,
)


class TestDataclasses:
    def test_api_auth_defaults(self):
        auth = APIAuth()
        assert auth.header_name == "Authorization"
        assert auth.token_env == "API_TOKEN"
        assert auth.prefix == "Bearer "

    def test_api_config_defaults(self):
        cfg = APIConfig()
        assert cfg.openapi is None
        assert cfg.base_url is None
        assert cfg.tags == []

    def test_legacy_config_default(self):
        cfg = LegacyQAAgentConfig.default()
        assert isinstance(cfg.api, APIConfig)


class TestLoadConfig:
    def test_load_from_explicit_path(self, tmp_path: Path):
        toml_content = (
            '[api]\n'
            'openapi = "spec.yaml"\n'
            'base_url = "http://localhost:9000"\n'
            'timeout = 30.0\n'
        )
        config_file = tmp_path / ".qaagent.toml"
        config_file.write_text(toml_content)

        cfg = load_config(config_file)

        assert cfg is not None
        assert cfg.api.openapi == "spec.yaml"
        assert cfg.api.base_url == "http://localhost:9000"
        assert cfg.api.timeout == 30.0

    def test_load_with_auth(self, tmp_path: Path):
        toml_content = (
            '[api]\n'
            'openapi = "spec.yaml"\n'
            '[api.auth]\n'
            'header_name = "X-API-Key"\n'
            'token_env = "MY_KEY"\n'
            'prefix = ""\n'
        )
        config_file = tmp_path / ".qaagent.toml"
        config_file.write_text(toml_content)

        cfg = load_config(config_file)

        assert cfg.api.auth.header_name == "X-API-Key"
        assert cfg.api.auth.token_env == "MY_KEY"
        assert cfg.api.auth.prefix == ""

    def test_load_with_tags_and_operations(self, tmp_path: Path):
        toml_content = (
            '[api]\n'
            'tags = ["public", "v2"]\n'
            'operations = ["getUser", "listItems"]\n'
        )
        config_file = tmp_path / ".qaagent.toml"
        config_file.write_text(toml_content)

        cfg = load_config(config_file)

        assert cfg.api.tags == ["public", "v2"]
        assert cfg.api.operations == ["getUser", "listItems"]

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        cfg = load_config(tmp_path / "missing.toml")
        assert cfg is None

    def test_load_no_path_no_env_no_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("QAAGENT_CONFIG", raising=False)

        cfg = load_config()
        assert cfg is None

    def test_load_from_env_var(self, tmp_path: Path, monkeypatch):
        toml_content = '[api]\nopenapi = "from_env.yaml"\n'
        config_file = tmp_path / "custom.toml"
        config_file.write_text(toml_content)
        monkeypatch.setenv("QAAGENT_CONFIG", str(config_file))

        cfg = load_config()

        assert cfg is not None
        assert cfg.api.openapi == "from_env.yaml"

    def test_load_from_cwd(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("QAAGENT_CONFIG", raising=False)
        toml_content = '[api]\nopenapi = "cwd_spec.yaml"\n'
        (tmp_path / ".qaagent.toml").write_text(toml_content)

        cfg = load_config()

        assert cfg is not None
        assert cfg.api.openapi == "cwd_spec.yaml"

    def test_load_invalid_toml(self, tmp_path: Path):
        config_file = tmp_path / "bad.toml"
        config_file.write_text("not valid toml {{{{")

        cfg = load_config(config_file)
        assert cfg is None


class TestWriteDefaultConfig:
    def test_creates_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = write_default_config(tmp_path / ".qaagent.toml")

        assert path.exists()
        content = path.read_text()
        assert "[api]" in content

    def test_does_not_overwrite(self, tmp_path: Path):
        config_file = tmp_path / ".qaagent.toml"
        config_file.write_text("existing content")

        path = write_default_config(config_file)

        assert path.read_text() == "existing content"


class TestWriteEnvExample:
    def test_creates_file(self, tmp_path: Path):
        path = write_env_example(tmp_path / ".env.example")

        assert path.exists()
        content = path.read_text()
        assert "API_TOKEN" in content

    def test_does_not_overwrite(self, tmp_path: Path):
        env_file = tmp_path / ".env.example"
        env_file.write_text("existing")

        path = write_env_example(env_file)

        assert path.read_text() == "existing"
