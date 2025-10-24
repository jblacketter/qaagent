"""
Repository cache manager.

Manages cached repositories in ~/.qaagent/repos/
Tracks metadata and provides listing/cleanup operations.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class RepoCache:
    """Manages cached cloned repositories."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the repository cache manager.

        Args:
            cache_dir: Directory for cached repos (default: ~/.qaagent/repos)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".qaagent" / "repos"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / ".cache_metadata.json"

    def list_cached_repos(self) -> List[dict]:
        """
        List all cached repositories.

        Returns:
            List of dicts with: url, path, cloned_at, last_accessed
        """
        metadata = self._load_metadata()
        cached_repos = []

        for url, info in metadata.items():
            local_path = Path(info["path"])
            if local_path.exists():
                cached_repos.append({
                    "url": url,
                    "path": str(local_path),
                    "cloned_at": info.get("cloned_at"),
                    "last_accessed": info.get("last_accessed"),
                    "size_mb": self._get_dir_size(local_path) / (1024 * 1024),
                })

        return cached_repos

    def register_clone(self, url: str, local_path: Path) -> None:
        """
        Register a newly cloned repository in the cache metadata.

        Args:
            url: Repository URL
            local_path: Local path to cloned repository
        """
        metadata = self._load_metadata()

        metadata[url] = {
            "path": str(local_path),
            "cloned_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
        }

        self._save_metadata(metadata)

    def update_access_time(self, url: str) -> None:
        """
        Update last accessed time for a repository.

        Args:
            url: Repository URL
        """
        metadata = self._load_metadata()

        if url in metadata:
            metadata[url]["last_accessed"] = datetime.now().isoformat()
            self._save_metadata(metadata)

    def remove_from_cache(self, url: str) -> bool:
        """
        Remove a repository from cache metadata and filesystem.

        Args:
            url: Repository URL

        Returns:
            True if removed, False if not found
        """
        metadata = self._load_metadata()

        if url not in metadata:
            return False

        # Remove from filesystem
        local_path = Path(metadata[url]["path"])
        if local_path.exists():
            import shutil

            shutil.rmtree(local_path)

        # Remove from metadata
        del metadata[url]
        self._save_metadata(metadata)

        return True

    def get_cache_stats(self) -> dict:
        """
        Get statistics about the repository cache.

        Returns:
            Dict with: total_repos, total_size_mb, oldest_repo, newest_repo
        """
        repos = self.list_cached_repos()

        if not repos:
            return {
                "total_repos": 0,
                "total_size_mb": 0,
                "oldest_repo": None,
                "newest_repo": None,
            }

        total_size = sum(r["size_mb"] for r in repos)

        # Find oldest and newest by cloned_at
        sorted_by_time = sorted(repos, key=lambda r: r.get("cloned_at", ""))

        return {
            "total_repos": len(repos),
            "total_size_mb": round(total_size, 2),
            "oldest_repo": sorted_by_time[0] if sorted_by_time else None,
            "newest_repo": sorted_by_time[-1] if sorted_by_time else None,
        }

    def cleanup_old_repos(self, days: int = 30) -> List[str]:
        """
        Clean up repositories not accessed in N days.

        Args:
            days: Number of days of inactivity before cleanup

        Returns:
            List of URLs that were cleaned up
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        cleaned = []

        for repo in self.list_cached_repos():
            last_accessed = datetime.fromisoformat(repo["last_accessed"])
            if last_accessed < cutoff:
                if self.remove_from_cache(repo["url"]):
                    cleaned.append(repo["url"])

        return cleaned

    def _load_metadata(self) -> dict:
        """Load cache metadata from JSON file."""
        if not self.metadata_file.exists():
            return {}

        try:
            return json.loads(self.metadata_file.read_text())
        except Exception:
            return {}

    def _save_metadata(self, metadata: dict) -> None:
        """Save cache metadata to JSON file."""
        self.metadata_file.write_text(json.dumps(metadata, indent=2))

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total
