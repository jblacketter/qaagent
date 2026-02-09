"""Configuration utilities for QA Agent."""
from __future__ import annotations

import warnings
from typing import Optional

from .legacy import (
    APIAuth,
    APIConfig,
    LegacyQAAgentConfig,
    load_config as load_legacy_config,
    write_default_config,
    write_env_example,
)
from .loader import (
    CONFIG_FILENAME,
    load_active_profile,
    load_profile,
    find_config_file,
    load_registry,
    save_registry,
    get_active_target,
)
from .manager import TargetManager
from .models import (
    AuthSettings,
    QAAgentProfile,
    ProjectSettings,
    EnvironmentSettings,
    OpenAPISettings,
    TestsSettings,
    SuiteSettings,
    DataSuiteSettings,
    ExcludeSettings,
    RiskAssessmentSettings,
    LLMSettings,
    TargetEntry,
    TargetRegistry,
)
from .templates import TemplateContext, available_templates, render_template

# Backwards compatibility
QAAgentConfig = LegacyQAAgentConfig
load_config = load_legacy_config


def _profile_to_legacy(profile: QAAgentProfile, project_root=None) -> LegacyQAAgentConfig:
    """Convert a QAAgentProfile to a LegacyQAAgentConfig for backward compat."""
    cfg = LegacyQAAgentConfig.default()

    # Map openapi spec_path
    if profile.openapi.spec_path:
        cfg.api.openapi = profile.openapi.spec_path

    # Map openapi filter settings
    if profile.openapi.tags:
        cfg.api.tags = list(profile.openapi.tags)
    if profile.openapi.operations:
        cfg.api.operations = list(profile.openapi.operations)
    if profile.openapi.endpoint_pattern:
        cfg.api.endpoint_pattern = profile.openapi.endpoint_pattern

    # Map base_url, auth, timeout from first available environment (prefer "dev")
    for env_name in ("dev", "staging", "production"):
        env = profile.app.get(env_name)
        if env and env.base_url:
            cfg.api.base_url = env.base_url
            if env.auth:
                cfg.api.auth.header_name = env.auth.header_name
                cfg.api.auth.token_env = env.auth.token_env
                cfg.api.auth.prefix = env.auth.prefix
            if env.timeout is not None:
                cfg.api.timeout = env.timeout
            break

    return cfg


def load_config_compat() -> Optional[LegacyQAAgentConfig]:
    """Load config with compatibility bridge.

    Priority order (local config always wins over global state):
      1. Local .qaagent.yaml in cwd
      2. Local .qaagent.toml in cwd (with deprecation warning)
      3. Global active-target profile (only when no local config exists)

    Returns a LegacyQAAgentConfig in all cases so callers don't need to change.
    """
    # Stage 1: Try local YAML config in cwd first (highest priority)
    config_file = find_config_file()
    if config_file:
        try:
            profile = load_profile(config_file)
            return _profile_to_legacy(profile)
        except Exception:
            pass

    # Stage 2: Try local legacy TOML in cwd (with deprecation warning)
    legacy = load_legacy_config()
    if legacy is not None:
        warnings.warn(
            "Loading config from .qaagent.toml is deprecated. "
            "Run `qaagent config migrate` to convert to .qaagent.yaml format.",
            DeprecationWarning,
            stacklevel=2,
        )
        return legacy

    # Stage 3: Fall back to global active-target profile
    try:
        entry, profile = load_active_profile()
        return _profile_to_legacy(profile, entry.resolved_path())
    except Exception:
        pass

    return None


__all__ = [
    "APIAuth",
    "APIConfig",
    "LegacyQAAgentConfig",
    "QAAgentConfig",
    "load_legacy_config",
    "load_config",
    "load_config_compat",
    "load_profile",
    "load_active_profile",
    "write_default_config",
    "write_env_example",
    "QAAgentProfile",
    "ProjectSettings",
    "EnvironmentSettings",
    "OpenAPISettings",
    "TestsSettings",
    "SuiteSettings",
    "DataSuiteSettings",
    "ExcludeSettings",
    "RiskAssessmentSettings",
    "LLMSettings",
    "TemplateContext",
    "available_templates",
    "render_template",
    "CONFIG_FILENAME",
    "find_config_file",
    "load_profile",
    "load_active_profile",
    "load_registry",
    "save_registry",
    "TargetEntry",
    "TargetRegistry",
    "get_active_target",
    "TargetManager",
]
