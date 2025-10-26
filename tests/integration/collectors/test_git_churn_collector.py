from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from qaagent.collectors.git_churn import GitChurnCollector
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager


def _setup_git_history(repo: Path) -> None:
    script = repo / "setup_git_history.py"
    subprocess.run([sys.executable, str(script)], cwd=repo, check=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_git_churn_collector(tmp_path: Path) -> None:
    fixtures = Path(__file__).parents[2] / "fixtures" / "synthetic_repo"
    repo_path = tmp_path / "synthetic_repo"
    shutil.copytree(fixtures, repo_path)

    _setup_git_history(repo_path)

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("synthetic", repo_path)

    writer = EvidenceWriter(handle)
    collector = GitChurnCollector()
    result = collector.run(handle, writer, EvidenceIDGenerator(handle.run_id))

    assert result.executed is True

    churn_file = handle.evidence_dir / "churn.jsonl"
    payloads = [json.loads(line) for line in churn_file.read_text().strip().splitlines()]
    session_stats = next((item for item in payloads if item["path"].endswith("src/auth/session.py")), None)
    assert session_stats is not None
    assert session_stats["commits"] >= 14

    manifest = json.loads(handle.manifest_path.read_text())
    assert manifest["tools"]["git-churn"]["executed"] is True
