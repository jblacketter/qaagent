"""Tests for AutoFixer and FixResult."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from qaagent.autofix import AutoFixer, FixResult


class TestFixResult:
    def test_defaults(self):
        result = FixResult(success=True, tool="test", files_modified=0, message="ok")
        assert result.errors == []

    def test_with_errors(self):
        result = FixResult(
            success=False, tool="test", files_modified=0, message="fail", errors=["e1"]
        )
        assert result.errors == ["e1"]


class TestAutoFixerFormatting:
    @patch.object(AutoFixer, "_check_tool_available", return_value=True)
    @patch("qaagent.autofix.subprocess.run")
    def test_autopep8_success(self, mock_run, mock_check, tmp_path):
        # Dry-run returns diff with 2 files
        dry_result = MagicMock(
            returncode=0,
            stdout="--- original/foo.py\n--- original/bar.py\n",
            stderr="",
        )
        # Actual run succeeds
        apply_result = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = [dry_result, apply_result]

        fixer = AutoFixer(tmp_path)
        result = fixer.fix_formatting(tool="autopep8")

        assert result.success
        assert result.tool == "autopep8"
        assert result.files_modified == 2

    @patch.object(AutoFixer, "_check_tool_available", return_value=False)
    def test_autopep8_not_installed(self, mock_check, tmp_path):
        fixer = AutoFixer(tmp_path)
        result = fixer.fix_formatting(tool="autopep8")

        assert not result.success
        assert "not installed" in result.message

    @patch.object(AutoFixer, "_check_tool_available", return_value=True)
    @patch("qaagent.autofix.subprocess.run")
    def test_autopep8_timeout(self, mock_run, mock_check, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["autopep8"], timeout=1800)

        fixer = AutoFixer(tmp_path)
        result = fixer.fix_formatting(tool="autopep8")

        assert not result.success
        assert "timed out" in result.message

    @patch.object(AutoFixer, "_check_tool_available", return_value=True)
    @patch("qaagent.autofix.subprocess.run")
    def test_black_success(self, mock_run, mock_check, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="reformatted foo.py\nreformatted bar.py\n",
            stderr="2 files reformatted",
        )

        fixer = AutoFixer(tmp_path)
        result = fixer.fix_formatting(tool="black")

        assert result.success
        assert result.tool == "black"
        assert result.files_modified == 3  # "reformatted" appears 3 times

    @patch.object(AutoFixer, "_check_tool_available", return_value=False)
    def test_black_not_installed(self, mock_check, tmp_path):
        fixer = AutoFixer(tmp_path)
        result = fixer.fix_formatting(tool="black")

        assert not result.success

    def test_unknown_tool(self, tmp_path):
        fixer = AutoFixer(tmp_path)
        result = fixer.fix_formatting(tool="unknown")

        assert not result.success
        assert "Unknown formatting tool" in result.message


class TestAutoFixerImports:
    @patch.object(AutoFixer, "_check_tool_available", return_value=True)
    @patch("qaagent.autofix.subprocess.run")
    def test_isort_success(self, mock_run, mock_check, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Fixing foo.py\nFixing bar.py\n",
            stderr="",
        )

        fixer = AutoFixer(tmp_path)
        result = fixer.fix_imports()

        assert result.success
        assert result.tool == "isort"
        assert result.files_modified == 2

    @patch.object(AutoFixer, "_check_tool_available", return_value=False)
    def test_isort_not_installed(self, mock_check, tmp_path):
        fixer = AutoFixer(tmp_path)
        result = fixer.fix_imports()

        assert not result.success
        assert "not installed" in result.message

    @patch.object(AutoFixer, "_check_tool_available", return_value=True)
    @patch("qaagent.autofix.subprocess.run")
    def test_isort_exception(self, mock_run, mock_check, tmp_path):
        mock_run.side_effect = OSError("disk full")

        fixer = AutoFixer(tmp_path)
        result = fixer.fix_imports()

        assert not result.success
        assert "disk full" in result.message


class TestAutoFixerSecurity:
    def test_fix_security_issues(self, tmp_path):
        fixer = AutoFixer(tmp_path)
        results = fixer.fix_security_issues()

        assert "secrets" in results
        assert not results["secrets"].success  # Manual review required

    def test_fix_security_issues_dry_run(self, tmp_path):
        fixer = AutoFixer(tmp_path)
        results = fixer.fix_security_issues(dry_run=True)

        assert "secrets" in results


class TestAutoFixerGenerateCommands:
    def test_formatting_findings(self, tmp_path):
        fixer = AutoFixer(tmp_path)
        findings = [
            {"tool": "flake8", "code": "W293", "file": "foo.py"},
        ]
        commands = fixer.generate_fix_commands(findings)

        assert len(commands) == 1
        assert "autopep8" in commands[0]["command"]

    def test_import_findings(self, tmp_path):
        fixer = AutoFixer(tmp_path)
        findings = [
            {"tool": "flake8", "code": "E401", "file": "bar.py"},
        ]
        commands = fixer.generate_fix_commands(findings)

        assert any("isort" in c["command"] for c in commands)

    def test_empty_findings_returns_default(self, tmp_path):
        fixer = AutoFixer(tmp_path)
        commands = fixer.generate_fix_commands([])

        assert len(commands) == 1
        assert "autopep8" in commands[0]["command"]

    def test_deduplicates_tools(self, tmp_path):
        fixer = AutoFixer(tmp_path)
        findings = [
            {"tool": "flake8", "code": "W293", "file": "a.py"},
            {"tool": "flake8", "code": "E501", "file": "b.py"},
        ]
        commands = fixer.generate_fix_commands(findings)

        autopep8_cmds = [c for c in commands if "autopep8" in c["command"]]
        assert len(autopep8_cmds) == 1


class TestAutoFixerCheckTool:
    @patch("qaagent.autofix.subprocess.run")
    def test_tool_available(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)

        fixer = AutoFixer(tmp_path)
        assert fixer._check_tool_available("black") is True

    @patch("qaagent.autofix.subprocess.run", side_effect=FileNotFoundError)
    def test_tool_not_found(self, mock_run, tmp_path):
        fixer = AutoFixer(tmp_path)
        assert fixer._check_tool_available("nonexistent") is False

    @patch(
        "qaagent.autofix.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["slow"], timeout=5),
    )
    def test_tool_timeout(self, mock_run, tmp_path):
        fixer = AutoFixer(tmp_path)
        assert fixer._check_tool_available("slow") is False
