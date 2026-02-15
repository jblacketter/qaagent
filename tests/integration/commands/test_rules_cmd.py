"""Integration tests for the qaagent rules CLI commands."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from qaagent.commands import app
from qaagent.config.models import (
    ProjectSettings,
    QAAgentProfile,
    RiskAssessmentSettings,
    TargetEntry,
)

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "data"


def _make_entry_profile(
    tmp_path: Path,
    *,
    custom_rules: list | None = None,
    custom_rules_file: str | None = None,
    severity_overrides: dict | None = None,
) -> tuple:
    """Build a (TargetEntry, QAAgentProfile) tuple for mocking load_active_profile."""
    entry = TargetEntry(name="test", path=str(tmp_path))
    ra = RiskAssessmentSettings(
        custom_rules=custom_rules or [],
        custom_rules_file=custom_rules_file,
        severity_overrides=severity_overrides or {},
    )
    profile = QAAgentProfile(
        project=ProjectSettings(name="test"),
        risk_assessment=ra,
    )
    return entry, profile


class TestRulesList:
    def test_list_shows_builtin_rules(self):
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "list"])
        assert result.exit_code == 0
        assert "SEC-001" in result.output
        assert "PERF-001" in result.output
        assert "REL-001" in result.output
        assert "built-in" in result.output

    def test_list_shows_rule_count(self):
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "list"])
        assert result.exit_code == 0
        assert "16 rules total" in result.output


class TestRulesShow:
    def test_show_existing_rule(self):
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "show", "SEC-001"])
        assert result.exit_code == 0
        assert "SEC-001" in result.output
        assert "built-in" in result.output
        assert "security" in result.output

    def test_show_nonexistent_rule(self):
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "show", "NONEXISTENT"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestRulesValidate:
    def test_validate_valid_file(self):
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "validate", str(FIXTURES / "custom_rules_valid.yaml")])
        assert result.exit_code == 0
        assert "Valid" in result.output
        assert "3 rule(s)" in result.output
        assert "CUSTOM-001" in result.output

    def test_validate_invalid_file(self):
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "validate", str(FIXTURES / "custom_rules_invalid.yaml")])
        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_validate_nonexistent_file(self):
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "validate", "/nonexistent/rules.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_validate_no_args_no_profile(self):
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "validate"])
        assert result.exit_code == 0
        assert "No custom rules" in result.output

    def test_validate_builtin_collision(self, tmp_path):
        collision_file = tmp_path / "bad_rules.yaml"
        collision_file.write_text(
            "rules:\n"
            "  - rule_id: SEC-001\n"
            "    category: security\n"
            "    severity: low\n"
            "    title: Collision\n"
            "    description: D\n"
            "    recommendation: R\n"
            "    match: {}\n"
        )
        with patch("qaagent.commands.rules_cmd.load_active_profile", return_value=None):
            result = runner.invoke(app, ["rules", "validate", str(collision_file)])
        assert result.exit_code == 1
        assert "collides with a built-in" in result.output


class TestRulesWithActiveProfile:
    """Tests exercising the load_active_profile() tuple-return path."""

    def test_list_with_active_profile(self, tmp_path):
        entry, profile = _make_entry_profile(tmp_path)
        with patch(
            "qaagent.commands.rules_cmd.load_active_profile",
            return_value=(entry, profile),
        ):
            result = runner.invoke(app, ["rules", "list"])
        assert result.exit_code == 0
        assert "SEC-001" in result.output

    def test_list_with_custom_rules_file(self, tmp_path):
        entry, profile = _make_entry_profile(
            tmp_path,
            custom_rules_file="custom_rules_valid.yaml",
        )
        # Copy fixture into the tmp_path (project root) so resolve finds it
        import shutil

        shutil.copy(FIXTURES / "custom_rules_valid.yaml", tmp_path / "custom_rules_valid.yaml")
        with patch(
            "qaagent.commands.rules_cmd.load_active_profile",
            return_value=(entry, profile),
        ):
            result = runner.invoke(app, ["rules", "list"])
        assert result.exit_code == 0
        assert "CUSTOM-001" in result.output
        assert "custom" in result.output

    def test_show_with_active_profile(self, tmp_path):
        entry, profile = _make_entry_profile(tmp_path)
        with patch(
            "qaagent.commands.rules_cmd.load_active_profile",
            return_value=(entry, profile),
        ):
            result = runner.invoke(app, ["rules", "show", "SEC-001"])
        assert result.exit_code == 0
        assert "SEC-001" in result.output

    def test_validate_inline_rules_from_profile(self, tmp_path):
        inline_rule = {
            "rule_id": "CUSTOM-INLINE-001",
            "category": "security",
            "severity": "high",
            "title": "Inline test rule",
            "description": "For testing",
            "recommendation": "Fix it",
            "match": {},
        }
        entry, profile = _make_entry_profile(tmp_path, custom_rules=[inline_rule])
        with patch(
            "qaagent.commands.rules_cmd.load_active_profile",
            return_value=(entry, profile),
        ):
            result = runner.invoke(app, ["rules", "validate"])
        assert result.exit_code == 0
        assert "1 rule(s) from inline" in result.output
        assert "CUSTOM-INLINE-001" in result.output

    def test_validate_custom_rules_file_only(self, tmp_path):
        """No-arg validate with only custom_rules_file (no inline rules)."""
        import shutil

        shutil.copy(FIXTURES / "custom_rules_valid.yaml", tmp_path / "rules.yaml")
        entry, profile = _make_entry_profile(
            tmp_path,
            custom_rules_file="rules.yaml",
        )
        with patch(
            "qaagent.commands.rules_cmd.load_active_profile",
            return_value=(entry, profile),
        ):
            result = runner.invoke(app, ["rules", "validate"])
        assert result.exit_code == 0
        assert "3 rule(s) from file" in result.output
        assert "CUSTOM-001" in result.output

    def test_validate_file_plus_inline(self, tmp_path):
        """No-arg validate with both file and inline rules."""
        import shutil

        shutil.copy(FIXTURES / "custom_rules_valid.yaml", tmp_path / "rules.yaml")
        inline_rule = {
            "rule_id": "CUSTOM-INLINE-099",
            "category": "reliability",
            "severity": "low",
            "title": "Inline extra rule",
            "description": "Testing merge",
            "recommendation": "N/A",
            "match": {},
        }
        entry, profile = _make_entry_profile(
            tmp_path,
            custom_rules_file="rules.yaml",
            custom_rules=[inline_rule],
        )
        with patch(
            "qaagent.commands.rules_cmd.load_active_profile",
            return_value=(entry, profile),
        ):
            result = runner.invoke(app, ["rules", "validate"])
        assert result.exit_code == 0
        assert "4 rule(s) from file (rules.yaml) + inline" in result.output
        assert "CUSTOM-001" in result.output
        assert "CUSTOM-INLINE-099" in result.output

    def test_validate_file_inline_duplicate_detected(self, tmp_path):
        """No-arg validate catches duplicate rule_id across file and inline."""
        import shutil

        shutil.copy(FIXTURES / "custom_rules_valid.yaml", tmp_path / "rules.yaml")
        # CUSTOM-001 already exists in the fixture file
        duplicate_rule = {
            "rule_id": "CUSTOM-001",
            "category": "security",
            "severity": "low",
            "title": "Duplicate",
            "description": "D",
            "recommendation": "R",
            "match": {},
        }
        entry, profile = _make_entry_profile(
            tmp_path,
            custom_rules_file="rules.yaml",
            custom_rules=[duplicate_rule],
        )
        with patch(
            "qaagent.commands.rules_cmd.load_active_profile",
            return_value=(entry, profile),
        ):
            result = runner.invoke(app, ["rules", "validate"])
        assert result.exit_code == 1
        assert "Duplicate" in result.output

    def test_list_resolves_rules_file_relative_to_project_root(self, tmp_path):
        """custom_rules_file resolves against project root, not CWD."""
        # Put the rules file in a subdirectory of the project root
        rules_dir = tmp_path / "config"
        rules_dir.mkdir()
        import shutil

        shutil.copy(FIXTURES / "custom_rules_valid.yaml", rules_dir / "rules.yaml")

        entry, profile = _make_entry_profile(
            tmp_path,
            custom_rules_file="config/rules.yaml",
        )
        with patch(
            "qaagent.commands.rules_cmd.load_active_profile",
            return_value=(entry, profile),
        ):
            result = runner.invoke(app, ["rules", "list"])
        assert result.exit_code == 0
        assert "CUSTOM-001" in result.output
