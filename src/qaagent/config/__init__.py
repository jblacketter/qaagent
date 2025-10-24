"""Configuration utilities for QA Agent."""

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

__all__ = [
    "APIAuth",
    "APIConfig",
    "LegacyQAAgentConfig",
    "QAAgentConfig",
    "load_legacy_config",
    "load_config",
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
