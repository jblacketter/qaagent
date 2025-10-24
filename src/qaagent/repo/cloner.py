"""
Git repository cloner with support for GitHub, GitLab, and Bitbucket.

Handles:
- HTTPS and SSH URLs
- Authentication (token, SSH keys)
- Shallow clones for speed
- Branch selection
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class RepoCloner:
    """Clones and manages Git repositories."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the repository cloner.

        Args:
            cache_dir: Directory to cache cloned repos (default: ~/.qaagent/repos)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".qaagent" / "repos"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse_repo_url(self, url: str) -> dict:
        """
        Parse a repository URL and extract components.

        Supports:
        - https://github.com/owner/repo
        - git@github.com:owner/repo.git
        - https://github.com/owner/repo.git

        Args:
            url: Repository URL

        Returns:
            Dict with: host, owner, repo, protocol, full_url
        """
        # Normalize URL
        url = url.strip()

        # SSH format: git@github.com:owner/repo.git
        ssh_pattern = r"git@([^:]+):([^/]+)/(.+?)(?:\.git)?$"
        ssh_match = re.match(ssh_pattern, url)
        if ssh_match:
            host, owner, repo = ssh_match.groups()
            return {
                "host": host,
                "owner": owner,
                "repo": repo,
                "protocol": "ssh",
                "full_url": url if url.endswith(".git") else f"{url}.git",
            }

        # HTTPS format
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            # Extract path: /owner/repo or /owner/repo.git
            path = parsed.path.strip("/")
            path = path.removesuffix(".git")
            parts = path.split("/")

            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1]
                return {
                    "host": parsed.netloc,
                    "owner": owner,
                    "repo": repo,
                    "protocol": "https",
                    "full_url": url if url.endswith(".git") else f"{url}.git",
                }

        raise ValueError(f"Invalid repository URL: {url}")

    def get_local_path(self, url: str) -> Path:
        """
        Get the local path where a repository would be cloned.

        Args:
            url: Repository URL

        Returns:
            Path to local clone directory
        """
        info = self.parse_repo_url(url)
        # Structure: ~/.qaagent/repos/<host>/<owner>/<repo>
        return self.cache_dir / info["host"] / info["owner"] / info["repo"]

    def is_cloned(self, url: str) -> bool:
        """
        Check if a repository is already cloned.

        Args:
            url: Repository URL

        Returns:
            True if repository exists locally
        """
        local_path = self.get_local_path(url)
        if not local_path.exists():
            return False

        # Check if it's a valid git repository
        git_dir = local_path / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def clone(
        self,
        url: str,
        branch: Optional[str] = None,
        depth: Optional[int] = 1,
        force: bool = False,
    ) -> Path:
        """
        Clone a repository or return existing clone.

        Args:
            url: Repository URL
            branch: Branch to clone (default: default branch)
            depth: Clone depth for shallow clones (1 = latest commit only)
            force: Force re-clone if already exists

        Returns:
            Path to cloned repository

        Raises:
            subprocess.CalledProcessError: If git clone fails
        """
        local_path = self.get_local_path(url)

        # If already cloned and not forcing, return existing path
        if self.is_cloned(url) and not force:
            return local_path

        # Remove existing clone if forcing
        if force and local_path.exists():
            import shutil

            shutil.rmtree(local_path)

        # Prepare clone directory
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Build git clone command
        cmd = ["git", "clone"]

        # Add depth for shallow clone (faster)
        if depth is not None:
            cmd.extend(["--depth", str(depth)])

        # Add branch if specified
        if branch:
            cmd.extend(["--branch", branch])

        # Add URL and destination
        info = self.parse_repo_url(url)
        clone_url = self._prepare_clone_url(info)
        cmd.extend([clone_url, str(local_path)])

        # Clone repository
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone repository: {e.stderr}") from e
        except subprocess.TimeoutExpired:
            raise RuntimeError("Repository clone timed out after 5 minutes")

        return local_path

    def update(self, url: str) -> Path:
        """
        Update an existing cloned repository (git pull).

        Args:
            url: Repository URL

        Returns:
            Path to updated repository

        Raises:
            RuntimeError: If repository not cloned or update fails
        """
        if not self.is_cloned(url):
            raise RuntimeError(f"Repository not cloned: {url}")

        local_path = self.get_local_path(url)

        try:
            # git pull
            subprocess.run(
                ["git", "pull"],
                cwd=local_path,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to update repository: {e.stderr}") from e

        return local_path

    def _prepare_clone_url(self, info: dict) -> str:
        """
        Prepare clone URL with authentication if needed.

        Checks for:
        - GITHUB_TOKEN environment variable
        - SSH key access

        Args:
            info: Parsed repository info

        Returns:
            Clone URL (may include token for HTTPS)
        """
        # For SSH, return as-is
        if info["protocol"] == "ssh":
            return info["full_url"]

        # For HTTPS, check for token
        if info["host"] == "github.com":
            token = os.environ.get("GITHUB_TOKEN")
            if token:
                # Format: https://token@github.com/owner/repo.git
                return f"https://{token}@{info['host']}/{info['owner']}/{info['repo']}.git"

        # Return standard HTTPS URL
        return info["full_url"]

    def get_repo_info(self, local_path: Path) -> dict:
        """
        Get information about a cloned repository.

        Args:
            local_path: Path to local repository

        Returns:
            Dict with: remote_url, branch, commit_hash, commit_message
        """
        if not (local_path / ".git").exists():
            raise ValueError(f"Not a git repository: {local_path}")

        info = {}

        try:
            # Get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=local_path,
                capture_output=True,
                text=True,
                check=True,
            )
            info["remote_url"] = result.stdout.strip()

            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=local_path,
                capture_output=True,
                text=True,
                check=True,
            )
            info["branch"] = result.stdout.strip()

            # Get latest commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=local_path,
                capture_output=True,
                text=True,
                check=True,
            )
            info["commit_hash"] = result.stdout.strip()

            # Get latest commit message
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=%B"],
                cwd=local_path,
                capture_output=True,
                text=True,
                check=True,
            )
            info["commit_message"] = result.stdout.strip()

        except subprocess.CalledProcessError:
            pass

        return info
