"""Unit tests for RepoCloner."""

from __future__ import annotations

from pathlib import Path

import pytest

from qaagent.repo.cloner import RepoCloner


class TestRepoCloner:
    """Test suite for repository cloner."""

    def test_parse_github_https_url(self) -> None:
        """Test parsing GitHub HTTPS URL."""
        cloner = RepoCloner()

        info = cloner.parse_repo_url("https://github.com/owner/repo")

        assert info["host"] == "github.com"
        assert info["owner"] == "owner"
        assert info["repo"] == "repo"
        assert info["protocol"] == "https"
        assert info["full_url"] == "https://github.com/owner/repo.git"

    def test_parse_github_https_url_with_git(self) -> None:
        """Test parsing GitHub HTTPS URL already ending in .git."""
        cloner = RepoCloner()

        info = cloner.parse_repo_url("https://github.com/owner/repo.git")

        assert info["owner"] == "owner"
        assert info["repo"] == "repo"
        assert info["full_url"] == "https://github.com/owner/repo.git"

    def test_parse_github_ssh_url(self) -> None:
        """Test parsing GitHub SSH URL."""
        cloner = RepoCloner()

        info = cloner.parse_repo_url("git@github.com:owner/repo.git")

        assert info["host"] == "github.com"
        assert info["owner"] == "owner"
        assert info["repo"] == "repo"
        assert info["protocol"] == "ssh"
        assert info["full_url"] == "git@github.com:owner/repo.git"

    def test_parse_github_ssh_url_without_git(self) -> None:
        """Test parsing GitHub SSH URL without .git suffix."""
        cloner = RepoCloner()

        info = cloner.parse_repo_url("git@github.com:owner/repo")

        assert info["owner"] == "owner"
        assert info["repo"] == "repo"
        assert info["full_url"] == "git@github.com:owner/repo.git"

    def test_parse_gitlab_url(self) -> None:
        """Test parsing GitLab URL."""
        cloner = RepoCloner()

        info = cloner.parse_repo_url("https://gitlab.com/owner/repo")

        assert info["host"] == "gitlab.com"
        assert info["owner"] == "owner"
        assert info["repo"] == "repo"

    def test_parse_bitbucket_url(self) -> None:
        """Test parsing Bitbucket URL."""
        cloner = RepoCloner()

        info = cloner.parse_repo_url("https://bitbucket.org/owner/repo")

        assert info["host"] == "bitbucket.org"
        assert info["owner"] == "owner"
        assert info["repo"] == "repo"

    def test_parse_invalid_url(self) -> None:
        """Test that invalid URLs raise ValueError."""
        cloner = RepoCloner()

        with pytest.raises(ValueError, match="Invalid repository URL"):
            cloner.parse_repo_url("not-a-valid-url")

    def test_get_local_path(self, tmp_path: Path) -> None:
        """Test getting local path for a repository."""
        cloner = RepoCloner(cache_dir=tmp_path)

        local_path = cloner.get_local_path("https://github.com/owner/repo")

        expected = tmp_path / "github.com" / "owner" / "repo"
        assert local_path == expected

    def test_get_local_path_different_hosts(self, tmp_path: Path) -> None:
        """Test local paths are separated by host."""
        cloner = RepoCloner(cache_dir=tmp_path)

        github_path = cloner.get_local_path("https://github.com/owner/repo")
        gitlab_path = cloner.get_local_path("https://gitlab.com/owner/repo")

        assert "github.com" in str(github_path)
        assert "gitlab.com" in str(gitlab_path)
        assert github_path != gitlab_path

    def test_is_cloned_false_when_not_exists(self, tmp_path: Path) -> None:
        """Test is_cloned returns False when directory doesn't exist."""
        cloner = RepoCloner(cache_dir=tmp_path)

        assert cloner.is_cloned("https://github.com/owner/repo") is False

    def test_is_cloned_false_when_not_git_repo(self, tmp_path: Path) -> None:
        """Test is_cloned returns False when directory exists but not a git repo."""
        cloner = RepoCloner(cache_dir=tmp_path)

        # Create directory but not a git repo
        local_path = cloner.get_local_path("https://github.com/owner/repo")
        local_path.mkdir(parents=True)

        assert cloner.is_cloned("https://github.com/owner/repo") is False

    def test_is_cloned_true_when_git_repo(self, tmp_path: Path) -> None:
        """Test is_cloned returns True when valid git repository exists."""
        cloner = RepoCloner(cache_dir=tmp_path)

        # Create mock git repository
        local_path = cloner.get_local_path("https://github.com/owner/repo")
        local_path.mkdir(parents=True)
        (local_path / ".git").mkdir()

        assert cloner.is_cloned("https://github.com/owner/repo") is True

    def test_prepare_clone_url_https_without_token(self, tmp_path: Path, monkeypatch) -> None:
        """Test clone URL preparation without token."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        cloner = RepoCloner(cache_dir=tmp_path)

        info = {"protocol": "https", "host": "github.com", "owner": "owner", "repo": "repo", "full_url": "https://github.com/owner/repo.git"}
        url = cloner._prepare_clone_url(info)

        assert url == "https://github.com/owner/repo.git"
        assert "@" not in url  # No token

    def test_prepare_clone_url_https_with_token(self, tmp_path: Path, monkeypatch) -> None:
        """Test clone URL preparation with GitHub token."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token-123")
        cloner = RepoCloner(cache_dir=tmp_path)

        info = {"protocol": "https", "host": "github.com", "owner": "owner", "repo": "repo", "full_url": "https://github.com/owner/repo.git"}
        url = cloner._prepare_clone_url(info)

        assert "test-token-123@github.com" in url

    def test_prepare_clone_url_ssh(self, tmp_path: Path) -> None:
        """Test clone URL preparation for SSH (unchanged)."""
        cloner = RepoCloner(cache_dir=tmp_path)

        info = {"protocol": "ssh", "full_url": "git@github.com:owner/repo.git"}
        url = cloner._prepare_clone_url(info)

        assert url == "git@github.com:owner/repo.git"

    def test_cache_dir_creation(self, tmp_path: Path) -> None:
        """Test that cache directory is created if it doesn't exist."""
        cache_dir = tmp_path / "test_cache"
        assert not cache_dir.exists()

        cloner = RepoCloner(cache_dir=cache_dir)

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_default_cache_dir(self) -> None:
        """Test that default cache directory is ~/.qaagent/repos."""
        cloner = RepoCloner()

        expected = Path.home() / ".qaagent" / "repos"
        assert cloner.cache_dir == expected
