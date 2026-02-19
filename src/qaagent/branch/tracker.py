"""Branch tracker — discovers and tracks git branches for a repository."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from qaagent.branch.models import BranchCard, BranchStage
from qaagent.branch import store


# Common branch-name patterns that contain a story/ticket ID.
# Matches: feature/PROJ-123-desc, bugfix/PROJ-123, PROJ-123-something, etc.
_STORY_PATTERNS = [
    re.compile(r"(?:feature|bugfix|fix|hotfix|task|chore|story)[/-]([A-Z][A-Z0-9]+-\d+)", re.IGNORECASE),
    re.compile(r"^([A-Z][A-Z0-9]+-\d+)"),  # branch starts with PROJ-123
]


def extract_story_id(branch_name: str) -> Optional[str]:
    """Try to extract a story/ticket ID from a branch name.

    Examples:
        feature/PROJ-123-add-login  ->  PROJ-123
        bugfix/ABC-42               ->  ABC-42
        PROJ-99-quick-fix           ->  PROJ-99
        main                        ->  None
    """
    for pat in _STORY_PATTERNS:
        m = pat.search(branch_name)
        if m:
            return m.group(1).upper()
    return None


class BranchTracker:
    """Scans a git repository and syncs branch state to the store."""

    def __init__(self, repo_path: Path, repo_id: str, base_branch: str = "main"):
        self.repo_path = repo_path
        self.repo_id = repo_id
        self.base_branch = base_branch

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> list[BranchCard]:
        """Scan the repository for all branches and sync their lifecycle state.

        Returns the list of branch cards after syncing.
        """
        remote_branches = self._list_remote_branches()
        merged_branches = self._list_merged_branches()
        now = datetime.now(timezone.utc).isoformat()

        cards: list[BranchCard] = []
        for branch in remote_branches:
            if branch == self.base_branch:
                continue  # skip base branch itself

            existing = store.branch_get_by_name(self.repo_id, branch)
            stage = self._determine_stage(branch, merged_branches, existing)
            summary, commit_count, files_changed = self._branch_stats(branch)
            story_id = extract_story_id(branch)

            card = BranchCard(
                repo_id=self.repo_id,
                branch_name=branch,
                base_branch=self.base_branch,
                stage=stage,
                story_id=story_id if existing is None else (existing.story_id or story_id),
                story_url=existing.story_url if existing else None,
                notes=existing.notes if existing else None,
                change_summary=summary,
                commit_count=commit_count,
                files_changed=files_changed,
                first_seen_at=existing.first_seen_at if existing else now,
                last_updated_at=now,
                merged_at=existing.merged_at if existing else (now if stage == BranchStage.MERGED else None),
            )
            row_id = store.branch_upsert(card)
            card.id = row_id
            cards.append(card)

        return cards

    def refresh_card(self, branch_name: str) -> Optional[BranchCard]:
        """Refresh a single branch card."""
        merged = self._list_merged_branches()
        existing = store.branch_get_by_name(self.repo_id, branch_name)
        stage = self._determine_stage(branch_name, merged, existing)
        summary, commit_count, files_changed = self._branch_stats(branch_name)
        now = datetime.now(timezone.utc).isoformat()
        story_id = extract_story_id(branch_name)

        card = BranchCard(
            repo_id=self.repo_id,
            branch_name=branch_name,
            base_branch=self.base_branch,
            stage=stage,
            story_id=story_id if existing is None else (existing.story_id or story_id),
            story_url=existing.story_url if existing else None,
            notes=existing.notes if existing else None,
            change_summary=summary,
            commit_count=commit_count,
            files_changed=files_changed,
            first_seen_at=existing.first_seen_at if existing else now,
            last_updated_at=now,
            merged_at=existing.merged_at if existing else (now if stage == BranchStage.MERGED else None),
        )
        row_id = store.branch_upsert(card)
        card.id = row_id
        return card

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    def _run_git(self, *args: str) -> str:
        """Run a git command and return stdout."""
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()

    def _list_remote_branches(self) -> list[str]:
        """List all remote-tracking branches (stripped of origin/ prefix)."""
        # First fetch to get latest state
        try:
            subprocess.run(
                ["git", "fetch", "--prune"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass  # best-effort fetch

        output = self._run_git("branch", "-r", "--format=%(refname:short)")
        branches: list[str] = []
        for line in output.splitlines():
            line = line.strip()
            if not line or "HEAD" in line:
                continue
            # Strip origin/ prefix
            if line.startswith("origin/"):
                line = line[len("origin/"):]
            branches.append(line)
        return branches

    def _list_merged_branches(self) -> set[str]:
        """List branches that have been merged into the base branch."""
        output = self._run_git("branch", "-r", "--merged", f"origin/{self.base_branch}", "--format=%(refname:short)")
        merged: set[str] = set()
        for line in output.splitlines():
            line = line.strip()
            if not line or "HEAD" in line:
                continue
            if line.startswith("origin/"):
                line = line[len("origin/"):]
            merged.add(line)
        return merged

    def _branch_stats(self, branch: str) -> tuple[str, int, int]:
        """Get commit summary, count, and files changed for a branch vs base.

        Returns (summary_text, commit_count, files_changed).
        """
        # Commit count ahead of base
        count_output = self._run_git(
            "rev-list", "--count", f"origin/{self.base_branch}..origin/{branch}"
        )
        try:
            commit_count = int(count_output)
        except ValueError:
            commit_count = 0

        # Files changed
        diff_output = self._run_git(
            "diff", "--name-only", f"origin/{self.base_branch}...origin/{branch}"
        )
        changed_files = [f for f in diff_output.splitlines() if f.strip()]
        files_changed = len(changed_files)

        # Summary from commit messages
        log_output = self._run_git(
            "log", "--oneline", f"origin/{self.base_branch}..origin/{branch}",
            "--format=%s", "-20"
        )
        commits = [line.strip() for line in log_output.splitlines() if line.strip()]
        if commits:
            summary = "; ".join(commits[:5])
            if len(commits) > 5:
                summary += f" (+{len(commits) - 5} more)"
        else:
            summary = "No new commits"

        return summary, commit_count, files_changed

    def _determine_stage(
        self,
        branch: str,
        merged_branches: set[str],
        existing: Optional[BranchCard],
    ) -> BranchStage:
        """Determine the lifecycle stage of a branch.

        Automatic transitions: created -> active -> merged.
        Manual stages (qa, released) are preserved from existing card.
        """
        # If the branch has been manually moved to qa or released, keep it
        if existing and existing.stage in (BranchStage.QA, BranchStage.RELEASED):
            return existing.stage

        # If merged into base
        if branch in merged_branches:
            return BranchStage.MERGED

        # Has commits ahead of base → active
        count_output = self._run_git(
            "rev-list", "--count", f"origin/{self.base_branch}..origin/{branch}"
        )
        try:
            count = int(count_output)
        except ValueError:
            count = 0

        if count > 0:
            return BranchStage.ACTIVE

        return BranchStage.CREATED
