"""Collector for git churn statistics."""

from __future__ import annotations

import logging
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator, ChurnRecord
from qaagent.evidence.run_manager import RunHandle

from .base import CollectorResult

LOGGER = logging.getLogger(__name__)


@dataclass
class GitChurnConfig:
    window_days: int = 90


class GitChurnCollector:
    """Analyze recent git history to surface churn hotspots."""

    def __init__(self, config: Optional[GitChurnConfig] = None) -> None:
        self.config = config or GitChurnConfig()

    def run(
        self,
        handle: RunHandle,
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> CollectorResult:
        result = CollectorResult(tool_name="git-churn")
        repo_path = Path(handle.manifest.target.path)

        if not (repo_path / ".git").exists():
            msg = "Target is not a git repository"
            LOGGER.info(msg)
            result.diagnostics.append(msg)
            result.mark_finished()
            handle.register_tool("git-churn", result.to_tool_status())
            handle.write_manifest()
            return result

        since = datetime.now(timezone.utc) - timedelta(days=self.config.window_days)
        cmd = [
            "git",
            "log",
            f"--since={since.isoformat()}",
            "--pretty=format:commit:%H:%an:%aI",
            "--numstat",
        ]

        try:
            completed = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            msg = "git executable not found"
            LOGGER.warning(msg)
            result.diagnostics.append(msg)
            result.mark_finished()
            handle.register_tool("git-churn", result.to_tool_status())
            handle.write_manifest()
            return result
        except subprocess.TimeoutExpired:
            msg = "git log timed out"
            LOGGER.error(msg)
            result.errors.append(msg)
            result.mark_finished()
            handle.register_tool("git-churn", result.to_tool_status())
            handle.write_manifest()
            return result

        stdout = completed.stdout
        if stdout:
            artifact = handle.artifacts_dir / "git_churn.log"
            artifact.write_text(stdout if stdout.endswith("\n") else stdout + "\n", encoding="utf-8")

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            if stderr:
                result.errors.append(stderr)

        records = self._parse_log(stdout.splitlines())
        if records:
            payload = [
                ChurnRecord(
                    evidence_id=id_generator.next_id("chn"),
                    path=path,
                    window=f"{self.config.window_days}d",
                    commits=data["commits"],
                    lines_added=data["added"],
                    lines_deleted=data["deleted"],
                    contributors=len(data["authors"]),
                    last_commit_at=data["last_commit"],
                ).to_dict()
                for path, data in records.items()
            ]
            writer.write_records("churn", payload)
            result.executed = True
            result.findings.extend(payload)
        else:
            result.executed = False

        result.mark_finished()
        handle.register_tool("git-churn", result.to_tool_status())
        handle.write_manifest()
        return result

    def _parse_log(self, lines: List[str]) -> Dict[str, Dict[str, any]]:
        file_stats: Dict[str, Dict[str, any]] = defaultdict(
            lambda: {"commits": 0, "added": 0, "deleted": 0, "authors": set(), "last_commit": None}
        )
        current_commit: Optional[str] = None
        current_author: Optional[str] = None
        current_date: Optional[str] = None

        for line in lines:
            if line.startswith("commit:"):
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    current_commit = parts[1]
                    current_author = parts[2]
                    current_date = parts[3]
                continue
            if not line or current_commit is None:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, deleted, path = parts
            if path == "-" or path.endswith("/" ):
                continue
            try:
                added_int = int(added) if added.isdigit() else 0
            except ValueError:
                added_int = 0
            try:
                deleted_int = int(deleted) if deleted.isdigit() else 0
            except ValueError:
                deleted_int = 0

            stats = file_stats[path]
            stats["commits"] += 1
            stats["added"] += added_int
            stats["deleted"] += deleted_int
            if current_author:
                stats["authors"].add(current_author)
            if current_date:
                prev = stats["last_commit"]
                if prev is None or current_date > prev:
                    stats["last_commit"] = current_date

        return file_stats
