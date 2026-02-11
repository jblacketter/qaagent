"""Tests for repo/cache.py — RepoCache manager."""
from __future__ import annotations

import json
from pathlib import Path

from qaagent.repo.cache import RepoCache


class TestRepoCacheInit:
    def test_default_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        cache = RepoCache()
        assert cache.cache_dir == tmp_path / ".qaagent" / "repos"
        assert cache.cache_dir.is_dir()

    def test_custom_dir(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path / "my_cache")
        assert cache.cache_dir == tmp_path / "my_cache"
        assert cache.cache_dir.is_dir()


class TestRegisterAndList:
    def test_register_clone(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        (repo_dir / "file.py").write_text("pass")

        cache.register_clone("https://github.com/user/repo", repo_dir)

        repos = cache.list_cached_repos()
        assert len(repos) == 1
        assert repos[0]["url"] == "https://github.com/user/repo"
        assert repos[0]["size_mb"] > 0

    def test_list_empty(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        assert cache.list_cached_repos() == []

    def test_list_skips_missing_dirs(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        # Manually write metadata pointing to nonexistent path
        metadata = {
            "https://github.com/user/gone": {
                "path": str(tmp_path / "gone"),
                "cloned_at": "2026-01-01T00:00:00",
                "last_accessed": "2026-01-01T00:00:00",
            }
        }
        cache.metadata_file.write_text(json.dumps(metadata))

        repos = cache.list_cached_repos()
        assert len(repos) == 0


class TestAccessTime:
    def test_update_access_time(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        cache.register_clone("https://github.com/user/repo", repo_dir)

        original_time = json.loads(cache.metadata_file.read_text())["https://github.com/user/repo"]["last_accessed"]

        cache.update_access_time("https://github.com/user/repo")

        updated_time = json.loads(cache.metadata_file.read_text())["https://github.com/user/repo"]["last_accessed"]
        assert updated_time >= original_time

    def test_update_access_time_unknown_url(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        cache.update_access_time("https://unknown.com/repo")  # Should not raise


class TestRemove:
    def test_remove_existing(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "file.py").write_text("pass")
        cache.register_clone("https://github.com/user/repo", repo_dir)

        result = cache.remove_from_cache("https://github.com/user/repo")

        assert result is True
        assert not repo_dir.exists()
        assert cache.list_cached_repos() == []

    def test_remove_nonexistent(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        result = cache.remove_from_cache("https://unknown.com/repo")
        assert result is False


class TestCacheStats:
    def test_stats_empty(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        stats = cache.get_cache_stats()

        assert stats["total_repos"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["oldest_repo"] is None

    def test_stats_with_repos(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        for name in ["repo1", "repo2"]:
            d = tmp_path / name
            d.mkdir()
            (d / "f.txt").write_text("data" * 1000)
            cache.register_clone(f"https://github.com/user/{name}", d)

        stats = cache.get_cache_stats()

        assert stats["total_repos"] == 2
        assert stats["total_size_mb"] >= 0
        assert stats["oldest_repo"] is not None
        assert stats["newest_repo"] is not None


class TestCleanup:
    def test_cleanup_old_repos(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        repo_dir = tmp_path / "old-repo"
        repo_dir.mkdir()

        # Register with an old timestamp
        metadata = {
            "https://github.com/user/old": {
                "path": str(repo_dir),
                "cloned_at": "2025-01-01T00:00:00",
                "last_accessed": "2025-01-01T00:00:00",
            }
        }
        cache.metadata_file.write_text(json.dumps(metadata))

        cleaned = cache.cleanup_old_repos(days=1)

        assert "https://github.com/user/old" in cleaned
        assert not repo_dir.exists()

    def test_cleanup_keeps_recent(self, tmp_path):
        cache = RepoCache(cache_dir=tmp_path)
        repo_dir = tmp_path / "recent-repo"
        repo_dir.mkdir()
        cache.register_clone("https://github.com/user/recent", repo_dir)

        cleaned = cache.cleanup_old_repos(days=1)

        assert len(cleaned) == 0
        assert repo_dir.exists()
