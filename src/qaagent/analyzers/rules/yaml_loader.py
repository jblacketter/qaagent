"""YAML custom rule schema models and loaders."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from pydantic import BaseModel, Field, field_validator

from qaagent.analyzers.models import RiskCategory, RiskSeverity


class PathCondition(BaseModel):
    """Match conditions for route path."""

    equals: Optional[str] = None
    contains: Optional[str] = None
    regex: Optional[str] = None
    starts_with: Optional[str] = None
    not_contains: Optional[List[str]] = None

    @field_validator("regex", mode="before")
    @classmethod
    def _validate_regex(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                re.compile(v)
            except re.error as exc:
                raise ValueError(f"Invalid regex pattern: {exc}") from exc
        return v


class MethodCondition(BaseModel):
    """Match conditions for route HTTP method."""

    equals: Optional[str] = None
    in_: Optional[List[str]] = Field(None, alias="in")

    model_config = {"populate_by_name": True}


class AuthCondition(BaseModel):
    """Match conditions for route auth_required."""

    equals: Optional[bool] = None


class TagsCondition(BaseModel):
    """Match conditions for route tags."""

    contains: Optional[str] = None
    empty: Optional[bool] = None


class DeprecatedCondition(BaseModel):
    """Match conditions for route deprecated flag."""

    equals: Optional[bool] = None


class MatchCondition(BaseModel):
    """Top-level match block — all present conditions use AND logic."""

    path: Optional[PathCondition] = None
    method: Optional[MethodCondition] = None
    auth_required: Optional[AuthCondition] = None
    tags: Optional[TagsCondition] = None
    deprecated: Optional[DeprecatedCondition] = None


class SeverityEscalation(BaseModel):
    """Conditional severity override within a rule."""

    condition: MatchCondition
    severity: RiskSeverity


class CustomRuleDefinition(BaseModel):
    """Schema for a single custom risk rule defined in YAML."""

    rule_id: str
    category: RiskCategory
    severity: RiskSeverity
    title: str
    description: str
    recommendation: str
    match: MatchCondition
    severity_escalation: List[SeverityEscalation] = Field(default_factory=list)
    cwe_id: Optional[str] = None
    owasp_top_10: Optional[str] = None
    references: List[str] = Field(default_factory=list)


def load_rules_from_dicts(
    data: List[Dict[str, Any]],
    *,
    builtin_ids: Optional[Set[str]] = None,
    source_label: str = "inline custom_rules",
) -> List[CustomRuleDefinition]:
    """Parse a list of dicts into validated CustomRuleDefinition objects.

    Args:
        data: List of rule definition dicts (from .qaagent.yaml inline config).
        builtin_ids: Set of built-in rule IDs. Raises ValueError on collision.
        source_label: Label for error messages identifying the source.

    Returns:
        List of validated CustomRuleDefinition objects.

    Raises:
        ValueError: On validation errors or rule_id collisions with built-ins.
    """
    builtin_ids = builtin_ids or set()
    rules: List[CustomRuleDefinition] = []
    seen_ids: Set[str] = set()

    for i, entry in enumerate(data):
        rule = CustomRuleDefinition.model_validate(entry)

        if rule.rule_id in builtin_ids:
            raise ValueError(
                f"Custom rule '{rule.rule_id}' in {source_label} collides with "
                f"a built-in rule ID. Use a unique ID (e.g., 'CUSTOM-XXX')."
            )

        if rule.rule_id in seen_ids:
            raise ValueError(
                f"Duplicate rule_id '{rule.rule_id}' in {source_label}."
            )

        seen_ids.add(rule.rule_id)
        rules.append(rule)

    return rules


def load_rules_from_yaml(
    path: Path,
    *,
    builtin_ids: Optional[Set[str]] = None,
) -> List[CustomRuleDefinition]:
    """Load custom rules from a YAML file.

    Expected format:
        rules:
          - rule_id: "CUSTOM-001"
            ...

    Args:
        path: Path to the YAML file.
        builtin_ids: Set of built-in rule IDs. Raises ValueError on collision.

    Returns:
        List of validated CustomRuleDefinition objects.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: On parse/validation errors or rule_id collisions.
    """
    if not path.exists():
        raise FileNotFoundError(f"Custom rules file not found: {path}")

    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)

    if not isinstance(raw, dict) or "rules" not in raw:
        raise ValueError(
            f"Custom rules file must contain a top-level 'rules' key: {path}"
        )

    rules_data = raw["rules"]
    if not isinstance(rules_data, list):
        raise ValueError(
            f"'rules' must be a list in {path}"
        )

    return load_rules_from_dicts(
        rules_data,
        builtin_ids=builtin_ids,
        source_label=f"custom_rules_file ('{path.name}')",
    )


def merge_custom_rules(
    *,
    file_rules: Optional[List[Dict[str, Any]]] = None,
    file_path: Optional[Path] = None,
    inline_rules: Optional[List[Dict[str, Any]]] = None,
    builtin_ids: Optional[Set[str]] = None,
) -> List[CustomRuleDefinition]:
    """Load and merge custom rules from file and inline sources.

    Merge order: file rules first, inline rules second.
    Duplicate rule_id across sources raises ValueError.

    Args:
        file_rules: Pre-loaded file rules (alternative to file_path).
        file_path: Path to custom_rules_file YAML.
        inline_rules: Inline custom_rules dicts from .qaagent.yaml.
        builtin_ids: Set of built-in rule IDs for collision detection.

    Returns:
        Merged list of CustomRuleDefinition objects.
    """
    builtin_ids = builtin_ids or set()
    merged: List[CustomRuleDefinition] = []
    seen_ids: Set[str] = set()

    # 1. File rules first
    if file_path is not None:
        file_defs = load_rules_from_yaml(file_path, builtin_ids=builtin_ids)
        for defn in file_defs:
            seen_ids.add(defn.rule_id)
            merged.append(defn)

    # 2. Inline rules second
    if inline_rules:
        inline_defs = load_rules_from_dicts(
            inline_rules,
            builtin_ids=builtin_ids,
            source_label="inline custom_rules",
        )
        for defn in inline_defs:
            if defn.rule_id in seen_ids:
                raise ValueError(
                    f"Duplicate rule_id '{defn.rule_id}' found in both "
                    f"custom_rules_file and inline custom_rules. "
                    f"Use unique rule_id values across all sources."
                )
            merged.append(defn)

    return merged
