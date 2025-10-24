"""
Workspace management for generated artifacts.

The workspace provides a staging area for generated files (OpenAPI specs,
tests, reports) before they're applied to the target project. This allows
for review, iteration, and approval workflows.

Structure:
    ~/.qaagent/
        workspace/
            <target-name>/
                openapi.json
                openapi.yaml
                tests/
                    unit/
                    behave/
                reports/
                fixtures/
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


class Workspace:
    """Manages workspace directory for generated artifacts."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize workspace manager.

        Args:
            base_dir: Base directory for workspace (defaults to ~/.qaagent/workspace)
        """
        if base_dir is None:
            base_dir = Path.home() / ".qaagent" / "workspace"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_target_workspace(self, target_name: str) -> Path:
        """
        Get workspace directory for a target.

        Args:
            target_name: Name of the target

        Returns:
            Path to target's workspace directory
        """
        workspace = self.base_dir / target_name
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def get_openapi_path(self, target_name: str, format: str = "json") -> Path:
        """
        Get path for OpenAPI spec in workspace.

        Args:
            target_name: Name of the target
            format: File format (json or yaml)

        Returns:
            Path to OpenAPI spec file
        """
        workspace = self.get_target_workspace(target_name)
        return workspace / f"openapi.{format}"

    def get_tests_dir(self, target_name: str, test_type: str = "unit") -> Path:
        """
        Get directory for generated tests.

        Args:
            target_name: Name of the target
            test_type: Type of tests (unit, behave, etc.)

        Returns:
            Path to tests directory
        """
        workspace = self.get_target_workspace(target_name)
        tests_dir = workspace / "tests" / test_type
        tests_dir.mkdir(parents=True, exist_ok=True)
        return tests_dir

    def get_reports_dir(self, target_name: str) -> Path:
        """
        Get directory for reports.

        Args:
            target_name: Name of the target

        Returns:
            Path to reports directory
        """
        workspace = self.get_target_workspace(target_name)
        reports_dir = workspace / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir

    def get_fixtures_dir(self, target_name: str) -> Path:
        """
        Get directory for test fixtures/data.

        Args:
            target_name: Name of the target

        Returns:
            Path to fixtures directory
        """
        workspace = self.get_target_workspace(target_name)
        fixtures_dir = workspace / "fixtures"
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        return fixtures_dir

    def list_targets(self) -> list[str]:
        """
        List all targets with workspaces.

        Returns:
            List of target names
        """
        if not self.base_dir.exists():
            return []

        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def clean_target(self, target_name: str) -> None:
        """
        Clean workspace for a target.

        Args:
            target_name: Name of the target
        """
        workspace = self.base_dir / target_name
        if workspace.exists():
            shutil.rmtree(workspace)

    def clean_all(self) -> None:
        """Clean entire workspace."""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_workspace_info(self, target_name: str) -> dict:
        """
        Get information about a target's workspace.

        Args:
            target_name: Name of the target

        Returns:
            Dictionary with workspace info
        """
        workspace = self.base_dir / target_name
        if not workspace.exists():
            return {"exists": False}

        info = {
            "exists": True,
            "path": str(workspace),
            "files": {},
        }

        # Check for OpenAPI specs
        for ext in ["json", "yaml"]:
            spec_file = workspace / f"openapi.{ext}"
            if spec_file.exists():
                info["files"][f"openapi.{ext}"] = {
                    "size": spec_file.stat().st_size,
                    "modified": spec_file.stat().st_mtime,
                }

        # Check for tests
        tests_dir = workspace / "tests"
        if tests_dir.exists():
            info["files"]["tests"] = {
                "unit": len(list((tests_dir / "unit").glob("*.py")))
                if (tests_dir / "unit").exists()
                else 0,
                "behave": len(list((tests_dir / "behave").glob("*.feature")))
                if (tests_dir / "behave").exists()
                else 0,
            }

        # Check for reports
        reports_dir = workspace / "reports"
        if reports_dir.exists():
            info["files"]["reports"] = len(list(reports_dir.glob("*")))

        # Check for fixtures
        fixtures_dir = workspace / "fixtures"
        if fixtures_dir.exists():
            info["files"]["fixtures"] = len(list(fixtures_dir.glob("*")))

        return info

    def copy_to_target(
        self,
        target_name: str,
        target_path: Path,
        file_pattern: str = "*",
        dry_run: bool = False,
    ) -> list[tuple[Path, Path]]:
        """
        Copy files from workspace to target project.

        Args:
            target_name: Name of the target
            target_path: Path to target project
            file_pattern: Pattern for files to copy (e.g., "*.json", "tests/*")
            dry_run: If True, only show what would be copied

        Returns:
            List of (source, destination) tuples
        """
        workspace = self.get_target_workspace(target_name)
        target_path = Path(target_path)

        copied = []
        for src_file in workspace.rglob(file_pattern):
            if src_file.is_file():
                # Calculate relative path from workspace
                rel_path = src_file.relative_to(workspace)
                dest_file = target_path / rel_path

                copied.append((src_file, dest_file))

                if not dry_run:
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)

        return copied
