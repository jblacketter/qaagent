"""Auto-fix capabilities for common code quality and security issues."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

LOGGER = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of applying a fix."""
    success: bool
    tool: str
    files_modified: int
    message: str
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class AutoFixer:
    """Automatically fix common code quality issues."""

    def __init__(self, target_path: Path):
        self.target_path = Path(target_path)

    def fix_formatting(self, tool: str = "autopep8") -> FixResult:
        """
        Auto-fix Python formatting issues.

        Args:
            tool: Formatting tool to use ('autopep8' or 'black')

        Returns:
            FixResult with details of what was fixed
        """
        if tool == "autopep8":
            return self._run_autopep8()
        elif tool == "black":
            return self._run_black()
        else:
            return FixResult(
                success=False,
                tool=tool,
                files_modified=0,
                message=f"Unknown formatting tool: {tool}",
                errors=[f"Supported tools: autopep8, black"],
            )

    def fix_imports(self) -> FixResult:
        """Auto-fix import sorting and unused imports using isort."""
        if not self._check_tool_available("isort"):
            return FixResult(
                success=False,
                tool="isort",
                files_modified=0,
                message="isort not installed",
                errors=["Install with: pip install isort"],
            )

        try:
            result = subprocess.run(
                ["isort", ".", "--profile", "black"],
                cwd=self.target_path,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes for large codebases
            )

            success = result.returncode == 0
            output = result.stdout + result.stderr

            # Count modified files
            modified_count = output.count("Fixing")

            return FixResult(
                success=success,
                tool="isort",
                files_modified=modified_count,
                message=f"Fixed imports in {modified_count} files" if success else "Failed to fix imports",
                errors=[result.stderr] if result.stderr and not success else [],
            )
        except Exception as e:
            LOGGER.error(f"Error running isort: {e}")
            return FixResult(
                success=False,
                tool="isort",
                files_modified=0,
                message=f"Error running isort: {e}",
                errors=[str(e)],
            )

    def fix_security_issues(self, dry_run: bool = False) -> Dict[str, FixResult]:
        """
        Auto-fix common security issues.

        Args:
            dry_run: If True, only report what would be fixed

        Returns:
            Dictionary of fix results by issue type
        """
        results = {}

        # Fix hardcoded secrets detection (placeholder for now)
        results["secrets"] = FixResult(
            success=False,
            tool="secrets-detection",
            files_modified=0,
            message="Manual review required for secrets",
            errors=["Automatic secret removal not implemented for safety"],
        )

        return results

    def generate_fix_commands(self, findings: List[Dict]) -> List[Dict[str, str]]:
        """
        Generate shell commands to fix specific findings.

        Args:
            findings: List of finding dictionaries from evidence

        Returns:
            List of fix command dictionaries with 'description' and 'command'
        """
        commands = []
        tools_found = set()

        for finding in findings:
            tool = finding.get("tool", "")
            code = finding.get("code", "")
            file_path = finding.get("file", "")

            # Formatting issues
            if tool == "flake8" and code in ("W293", "W292", "E501"):
                if "autopep8" not in tools_found:
                    commands.append({
                        "description": "Fix formatting issues (whitespace, line length)",
                        "command": "autopep8 --in-place --aggressive --recursive .",
                    })
                    tools_found.add("autopep8")

            # Import issues
            if tool in ("flake8", "pylint") and any(x in code for x in ("E401", "I", "import")):
                if "isort" not in tools_found:
                    commands.append({
                        "description": "Sort and organize imports",
                        "command": "isort . --profile black",
                    })
                    tools_found.add("isort")

        # Add general cleanup command
        if not commands:
            commands.append({
                "description": "Run comprehensive formatting",
                "command": "autopep8 --in-place --aggressive --recursive . && isort . --profile black",
            })

        return commands

    def _run_autopep8(self) -> FixResult:
        """Run autopep8 to fix PEP 8 formatting issues."""
        if not self._check_tool_available("autopep8"):
            return FixResult(
                success=False,
                tool="autopep8",
                files_modified=0,
                message="autopep8 not installed",
                errors=["Install with: pip install autopep8"],
            )

        try:
            # First, do a dry-run to count files that would be modified
            dry_result = subprocess.run(
                ["autopep8", "--diff", "--recursive", "--aggressive", "."],
                cwd=self.target_path,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes for large codebases
            )

            # Count files in diff output
            modified_count = dry_result.stdout.count("--- original/")

            # Now actually apply fixes
            result = subprocess.run(
                ["autopep8", "--in-place", "--recursive", "--aggressive", "."],
                cwd=self.target_path,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes for large codebases
            )

            success = result.returncode == 0

            return FixResult(
                success=success,
                tool="autopep8",
                files_modified=modified_count,
                message=f"Fixed formatting in {modified_count} files" if success else "Failed to fix formatting",
                errors=[result.stderr] if result.stderr and not success else [],
            )
        except subprocess.TimeoutExpired:
            return FixResult(
                success=False,
                tool="autopep8",
                files_modified=0,
                message="autopep8 timed out",
                errors=["Process took longer than 30 minutes"],
            )
        except Exception as e:
            LOGGER.error(f"Error running autopep8: {e}")
            return FixResult(
                success=False,
                tool="autopep8",
                files_modified=0,
                message=f"Error running autopep8: {e}",
                errors=[str(e)],
            )

    def _run_black(self) -> FixResult:
        """Run black to fix formatting issues."""
        if not self._check_tool_available("black"):
            return FixResult(
                success=False,
                tool="black",
                files_modified=0,
                message="black not installed",
                errors=["Install with: pip install black"],
            )

        try:
            result = subprocess.run(
                ["black", "."],
                cwd=self.target_path,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes for large codebases
            )

            success = result.returncode == 0
            output = result.stdout + result.stderr

            # Count reformatted files
            modified_count = output.count("reformatted")

            return FixResult(
                success=success,
                tool="black",
                files_modified=modified_count,
                message=f"Formatted {modified_count} files" if success else "Failed to format files",
                errors=[result.stderr] if result.stderr and not success else [],
            )
        except Exception as e:
            LOGGER.error(f"Error running black: {e}")
            return FixResult(
                success=False,
                tool="black",
                files_modified=0,
                message=f"Error running black: {e}",
                errors=[str(e)],
            )

    def _check_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH."""
        try:
            subprocess.run(
                [tool, "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
