from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import os


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        pass


_load_dotenv_if_available()


@dataclass
class APIAuth:
    header_name: str = "Authorization"
    token_env: str = "API_TOKEN"
    prefix: str = "Bearer "


@dataclass
class APIConfig:
    openapi: Optional[str] = None  # path or URL
    base_url: Optional[str] = None
    auth: APIAuth = field(default_factory=APIAuth)
    timeout: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    endpoint_pattern: Optional[str] = None


@dataclass
class LegacyQAAgentConfig:
    api: APIConfig = field(default_factory=APIConfig)

    @staticmethod
    def default() -> "LegacyQAAgentConfig":
        return LegacyQAAgentConfig()


def load_config(path: Optional[str | Path] = None) -> Optional[LegacyQAAgentConfig]:
    import sys

    data: dict | None = None
    file_path: Optional[Path] = None

    # explicit path
    if path:
        p = Path(path)
        if p.exists():
            file_path = p
    else:
        # env override
        env_path = os.environ.get("QAAGENT_CONFIG")
        if env_path and Path(env_path).exists():
            file_path = Path(env_path)
        else:
            # search in cwd
            cand = Path(".qaagent.toml")
            if cand.exists():
                file_path = cand

    if not file_path:
        return None

    try:
        import tomllib  # Python 3.11+

        data = tomllib.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    cfg = LegacyQAAgentConfig.default()
    api = data.get("api", {}) if isinstance(data, dict) else {}
    if isinstance(api, dict):
        cfg.api.openapi = api.get("openapi")
        cfg.api.base_url = api.get("base_url")
        auth = api.get("auth", {})
        if isinstance(auth, dict):
            cfg.api.auth.header_name = auth.get("header_name", cfg.api.auth.header_name)
            cfg.api.auth.token_env = auth.get("token_env", cfg.api.auth.token_env)
            cfg.api.auth.prefix = auth.get("prefix", cfg.api.auth.prefix)
        cfg.api.timeout = api.get("timeout")
        cfg.api.tags = list(api.get("tags", []) or [])
        cfg.api.operations = list(api.get("operations", []) or [])
        cfg.api.endpoint_pattern = api.get("endpoint_pattern")
    return cfg


def write_default_config(path: str | Path = ".qaagent.toml") -> Path:
    p = Path(path)
    if p.exists():
        return p
    content = (
        "# QAAgent configuration\n"
        "# Customize per project.\n\n"
        "[api]\n"
        "# openapi = \"openapi.yaml\"  # path or URL to spec\n"
        "# base_url = \"http://localhost:8000\"\n"
        "# timeout = 10.0\n"
        "# endpoint_pattern = \"/api/.*\"\n"
        "# tags = [\"public\"]\n"
        "# operations = [\"getUser\"]\n\n"
        "[api.auth]\n"
        "# header_name = \"Authorization\"\n"
        "# token_env = \"API_TOKEN\"\n"
        "# prefix = \"Bearer \"\n"
    )
    p.write_text(content, encoding="utf-8")
    return p


def write_env_example(path: str | Path = ".env.example") -> Path:
    p = Path(path)
    if p.exists():
        return p
    content = (
        "# Copy to .env and fill in values\n"
        "API_TOKEN=\n"
        "BASE_URL=http://localhost:8000\n"
    )
    p.write_text(content, encoding="utf-8")
    return p
