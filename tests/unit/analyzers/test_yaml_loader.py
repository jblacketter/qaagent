"""Tests for YAML custom rule schema parsing and loading."""
from __future__ import annotations

from pathlib import Path

import pytest

from qaagent.analyzers.rules.yaml_loader import (
    CustomRuleDefinition,
    MatchCondition,
    PathCondition,
    load_rules_from_dicts,
    load_rules_from_yaml,
    merge_custom_rules,
)

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "data"

# ------------------------------------------------------------------
# Schema validation
# ------------------------------------------------------------------


class TestCustomRuleDefinitionSchema:
    def test_valid_minimal(self):
        defn = CustomRuleDefinition.model_validate(
            {
                "rule_id": "TEST-001",
                "category": "security",
                "severity": "high",
                "title": "Test",
                "description": "desc",
                "recommendation": "rec",
                "match": {"path": {"contains": "/api"}},
            }
        )
        assert defn.rule_id == "TEST-001"
        assert defn.match.path is not None
        assert defn.match.path.contains == "/api"

    def test_invalid_category_rejected(self):
        with pytest.raises(Exception):
            CustomRuleDefinition.model_validate(
                {
                    "rule_id": "X",
                    "category": "not_a_category",
                    "severity": "high",
                    "title": "T",
                    "description": "D",
                    "recommendation": "R",
                    "match": {},
                }
            )

    def test_invalid_severity_rejected(self):
        with pytest.raises(Exception):
            CustomRuleDefinition.model_validate(
                {
                    "rule_id": "X",
                    "category": "security",
                    "severity": "super_high",
                    "title": "T",
                    "description": "D",
                    "recommendation": "R",
                    "match": {},
                }
            )

    def test_invalid_regex_rejected(self):
        with pytest.raises(ValueError, match="Invalid regex"):
            PathCondition.model_validate({"regex": "[invalid"})

    def test_valid_regex_accepted(self):
        cond = PathCondition.model_validate({"regex": "^/api/v\\d+/"})
        assert cond.regex == "^/api/v\\d+/"


# ------------------------------------------------------------------
# load_rules_from_dicts
# ------------------------------------------------------------------


class TestLoadRulesFromDicts:
    def _make_rule(self, rule_id="CUSTOM-001", **overrides):
        base = {
            "rule_id": rule_id,
            "category": "security",
            "severity": "medium",
            "title": "Test",
            "description": "D",
            "recommendation": "R",
            "match": {"path": {"contains": "/test"}},
        }
        base.update(overrides)
        return base

    def test_empty_list(self):
        assert load_rules_from_dicts([]) == []

    def test_single_valid_rule(self):
        rules = load_rules_from_dicts([self._make_rule()])
        assert len(rules) == 1
        assert rules[0].rule_id == "CUSTOM-001"

    def test_builtin_collision_raises(self):
        with pytest.raises(ValueError, match="collides with a built-in"):
            load_rules_from_dicts(
                [self._make_rule(rule_id="SEC-001")],
                builtin_ids={"SEC-001", "SEC-002"},
            )

    def test_duplicate_id_within_source_raises(self):
        with pytest.raises(ValueError, match="Duplicate rule_id"):
            load_rules_from_dicts([
                self._make_rule(rule_id="CUSTOM-001"),
                self._make_rule(rule_id="CUSTOM-001"),
            ])

    def test_no_collision_without_builtin_ids(self):
        # Without builtin_ids, no collision check
        rules = load_rules_from_dicts([self._make_rule(rule_id="SEC-001")])
        assert len(rules) == 1


# ------------------------------------------------------------------
# load_rules_from_yaml
# ------------------------------------------------------------------


class TestLoadRulesFromYaml:
    def test_valid_file(self):
        rules = load_rules_from_yaml(FIXTURES / "custom_rules_valid.yaml")
        assert len(rules) == 3
        assert rules[0].rule_id == "CUSTOM-001"
        assert rules[1].rule_id == "CUSTOM-002"
        assert rules[2].rule_id == "CUSTOM-003"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_rules_from_yaml(Path("/nonexistent/rules.yaml"))

    def test_invalid_file_bad_schema(self):
        with pytest.raises(Exception):
            load_rules_from_yaml(FIXTURES / "custom_rules_invalid.yaml")

    def test_missing_rules_key(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("not_rules: []")
        with pytest.raises(ValueError, match="top-level 'rules' key"):
            load_rules_from_yaml(bad)

    def test_rules_not_a_list(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("rules: 'not a list'")
        with pytest.raises(ValueError, match="must be a list"):
            load_rules_from_yaml(bad)

    def test_builtin_collision_in_file(self):
        with pytest.raises(ValueError, match="collides with a built-in"):
            load_rules_from_yaml(
                FIXTURES / "custom_rules_valid.yaml",
                builtin_ids={"CUSTOM-001"},
            )


# ------------------------------------------------------------------
# merge_custom_rules
# ------------------------------------------------------------------


class TestMergeCustomRules:
    def _rule_dict(self, rule_id):
        return {
            "rule_id": rule_id,
            "category": "security",
            "severity": "medium",
            "title": f"Rule {rule_id}",
            "description": "D",
            "recommendation": "R",
            "match": {"path": {"contains": "/test"}},
        }

    def test_file_only(self):
        merged = merge_custom_rules(
            file_path=FIXTURES / "custom_rules_valid.yaml",
        )
        assert len(merged) == 3

    def test_inline_only(self):
        merged = merge_custom_rules(
            inline_rules=[self._rule_dict("INLINE-001")],
        )
        assert len(merged) == 1
        assert merged[0].rule_id == "INLINE-001"

    def test_file_and_inline_unique_ids(self):
        merged = merge_custom_rules(
            file_path=FIXTURES / "custom_rules_valid.yaml",
            inline_rules=[self._rule_dict("INLINE-001")],
        )
        assert len(merged) == 4
        ids = [r.rule_id for r in merged]
        assert "CUSTOM-001" in ids
        assert "INLINE-001" in ids

    def test_file_and_inline_duplicate_raises(self, tmp_path):
        f = tmp_path / "rules.yaml"
        f.write_text(
            "rules:\n"
            "  - rule_id: DUP-001\n"
            "    category: security\n"
            "    severity: low\n"
            "    title: T\n"
            "    description: D\n"
            "    recommendation: R\n"
            "    match: {}\n"
        )
        with pytest.raises(ValueError, match="Duplicate rule_id 'DUP-001'"):
            merge_custom_rules(
                file_path=f,
                inline_rules=[self._rule_dict("DUP-001")],
            )

    def test_both_empty(self):
        merged = merge_custom_rules()
        assert merged == []

    def test_builtin_collision_across_sources(self):
        with pytest.raises(ValueError, match="collides with a built-in"):
            merge_custom_rules(
                inline_rules=[self._rule_dict("SEC-001")],
                builtin_ids={"SEC-001"},
            )
