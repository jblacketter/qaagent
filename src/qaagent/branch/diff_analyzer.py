"""Diff analyzer — computes branch diff vs. base and categorizes changes."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FileChange:
    """A single file changed in a branch diff."""

    path: str
    additions: int = 0
    deletions: int = 0
    status: str = "modified"  # added, modified, deleted, renamed


@dataclass
class DiffResult:
    """Result of analyzing a branch diff against its base."""

    branch_name: str
    base_branch: str
    files: list[FileChange] = field(default_factory=list)
    diff_hash: str = ""

    # Categorized file lists (derived from files)
    route_files: list[FileChange] = field(default_factory=list)
    test_files: list[FileChange] = field(default_factory=list)
    config_files: list[FileChange] = field(default_factory=list)
    migration_files: list[FileChange] = field(default_factory=list)
    other_files: list[FileChange] = field(default_factory=list)

    @property
    def total_additions(self) -> int:
        return sum(f.additions for f in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(f.deletions for f in self.files)


# File path patterns for categorization
_ROUTE_PATTERNS = (
    "routes/", "route/", "views/", "endpoints/", "controllers/", "api/",
    "handlers/", "pages/", "app/",
)
_ROUTE_SUFFIXES = ("_routes.py", "_views.py", "_api.py", "_controller.py", "_handler.py")

_TEST_PATTERNS = ("test_", "tests/", "spec/", "__tests__/", ".test.", ".spec.")

_CONFIG_PATTERNS = (
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
    "config/", "settings/", "dockerfile", "docker-compose",
    ".github/", ".gitlab-ci", "makefile",
)

_MIGRATION_PATTERNS = ("migration", "alembic/", "migrations/", "migrate/")


def _categorize_file(path: str) -> str:
    """Categorize a file path into route, test, config, migration, or other."""
    lower = path.lower()

    for pat in _MIGRATION_PATTERNS:
        if pat in lower:
            return "migration"

    for pat in _TEST_PATTERNS:
        if pat in lower:
            return "test"

    for pat in _ROUTE_PATTERNS:
        if pat in lower:
            return "route"
    for suffix in _ROUTE_SUFFIXES:
        if lower.endswith(suffix):
            return "route"

    for pat in _CONFIG_PATTERNS:
        if pat in lower:
            return "config"

    return "other"


class DiffAnalyzer:
    """Analyzes the diff between a branch and its base branch."""

    def __init__(self, repo_path: Path, base_branch: str = "main"):
        self.repo_path = repo_path
        self.base_branch = base_branch

    def analyze(self, branch_name: str) -> DiffResult:
        """Compute the diff of branch vs. base and categorize changed files.

        Args:
            branch_name: The branch to analyze (compared against base_branch).

        Returns:
            DiffResult with categorized file changes and a content hash.
        """
        files = self._get_diff_files(branch_name)
        diff_hash = self._compute_diff_hash(branch_name)

        result = DiffResult(
            branch_name=branch_name,
            base_branch=self.base_branch,
            files=files,
            diff_hash=diff_hash,
        )

        # Categorize files
        for fc in files:
            category = _categorize_file(fc.path)
            if category == "route":
                result.route_files.append(fc)
            elif category == "test":
                result.test_files.append(fc)
            elif category == "config":
                result.config_files.append(fc)
            elif category == "migration":
                result.migration_files.append(fc)
            else:
                result.other_files.append(fc)

        return result

    def get_diff_content(self, branch_name: str, file_path: str) -> str:
        """Get the actual diff content for a specific file."""
        return self._run_git(
            "diff", f"origin/{self.base_branch}...origin/{branch_name}",
            "--", file_path,
        )

    def _get_diff_files(self, branch_name: str) -> list[FileChange]:
        """Get list of changed files with stats between branch and base."""
        # --numstat gives additions/deletions per file
        numstat = self._run_git(
            "diff", "--numstat",
            f"origin/{self.base_branch}...origin/{branch_name}",
        )

        # --name-status gives the change type (A, M, D, R)
        name_status = self._run_git(
            "diff", "--name-status",
            f"origin/{self.base_branch}...origin/{branch_name}",
        )

        # Parse name-status for file statuses
        statuses: dict[str, str] = {}
        for line in name_status.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                status_code = parts[0][0]  # first char: A, M, D, R
                file_path = parts[-1]  # last part is the file path (handles renames)
                status_map = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}
                statuses[file_path] = status_map.get(status_code, "modified")

        # Parse numstat for additions/deletions
        files: list[FileChange] = []
        for line in numstat.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    additions = int(parts[0]) if parts[0] != "-" else 0
                    deletions = int(parts[1]) if parts[1] != "-" else 0
                except ValueError:
                    additions = 0
                    deletions = 0
                file_path = parts[2]
                files.append(FileChange(
                    path=file_path,
                    additions=additions,
                    deletions=deletions,
                    status=statuses.get(file_path, "modified"),
                ))

        return files

    def _compute_diff_hash(self, branch_name: str) -> str:
        """Compute a hash of the diff for staleness detection."""
        diff_output = self._run_git(
            "diff", f"origin/{self.base_branch}...origin/{branch_name}",
        )
        return hashlib.sha256(diff_output.encode("utf-8", errors="replace")).hexdigest()[:16]

    def _run_git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
