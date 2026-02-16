"""Pluggable risk rule engine."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import RiskRule, RiskRuleRegistry
from .security import (
    SEC001_UnauthenticatedMutation,
    SEC002_MissingCORS,
    SEC003_PathTraversal,
    SEC004_MassAssignment,
    SEC005_MissingRateLimit,
    SEC006_SensitiveQueryParams,
    SEC007_MissingInputValidation,
    SEC008_AdminWithoutElevatedAuth,
)
from .performance import (
    PERF001_MissingPagination,
    PERF002_UnboundedQuery,
    PERF003_N1Risk,
    PERF004_MissingCaching,
)
from .reliability import (
    REL001_DeprecatedOperation,
    REL002_MissingErrorSchema,
    REL003_InconsistentNaming,
    REL004_MissingHealthCheck,
)

__all__ = [
    "RiskRule",
    "RiskRuleRegistry",
    "default_registry",
    "BUILTIN_RULE_CLASSES",
]

BUILTIN_RULE_CLASSES = [
    SEC001_UnauthenticatedMutation,
    SEC002_MissingCORS,
    SEC003_PathTraversal,
    SEC004_MassAssignment,
    SEC005_MissingRateLimit,
    SEC006_SensitiveQueryParams,
    SEC007_MissingInputValidation,
    SEC008_AdminWithoutElevatedAuth,
    PERF001_MissingPagination,
    PERF002_UnboundedQuery,
    PERF003_N1Risk,
    PERF004_MissingCaching,
    REL001_DeprecatedOperation,
    REL002_MissingErrorSchema,
    REL003_InconsistentNaming,
    REL004_MissingHealthCheck,
]


def _builtin_ids() -> set[str]:
    return {cls().rule_id for cls in BUILTIN_RULE_CLASSES}


def default_registry(
    *,
    custom_rules: Optional[List[Dict[str, Any]]] = None,
    custom_rules_file: Optional[Path] = None,
    severity_overrides: Optional[Dict[str, str]] = None,
) -> RiskRuleRegistry:
    """Return a registry populated with built-in + optional custom rules.

    Args:
        custom_rules: Inline custom rule dicts from .qaagent.yaml.
        custom_rules_file: Path to a separate custom rules YAML file.
        severity_overrides: Map of rule_id -> severity string for post-eval remapping.
    """
    from .yaml_loader import merge_custom_rules
    from .yaml_rule import YamlRiskRule

    registry = RiskRuleRegistry()
    for rule_cls in BUILTIN_RULE_CLASSES:
        registry.register(rule_cls())

    # Load and register custom YAML rules
    if custom_rules or custom_rules_file:
        builtin = _builtin_ids()
        merged = merge_custom_rules(
            file_path=custom_rules_file,
            inline_rules=custom_rules,
            builtin_ids=builtin,
        )
        for defn in merged:
            registry.register(YamlRiskRule(defn))

    # Store severity overrides on the registry for run_all() to apply
    if severity_overrides:
        registry.severity_overrides = severity_overrides

    return registry
