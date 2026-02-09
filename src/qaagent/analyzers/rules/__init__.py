"""Pluggable risk rule engine."""
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
]


def default_registry() -> RiskRuleRegistry:
    """Return a registry populated with all built-in rules."""
    registry = RiskRuleRegistry()
    for rule_cls in [
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
    ]:
        registry.register(rule_cls())
    return registry
