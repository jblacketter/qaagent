from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from qaagent.collectors.orchestrator import CollectorsOrchestrator
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager


def _prepare_repo(tmp_path: Path) -> Path:
    fixtures = Path(__file__).parents[2] / "fixtures" / "synthetic_repo"
    repo_path = tmp_path / "synthetic_repo"
    shutil.copytree(fixtures, repo_path)
    subprocess.run([sys.executable, "setup_git_history.py"], cwd=repo_path, check=True)
    return repo_path


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


@pytest.mark.skipif(
    not _tool_available("flake8")
    or not _tool_available("pylint")
    or not _tool_available("bandit")
    or not _tool_available("pip-audit"),
    reason="Required tools not installed",
)
def test_collectors_orchestrator(tmp_path: Path) -> None:
    repo_path = _prepare_repo(tmp_path)

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("synthetic", repo_path)
    writer = EvidenceWriter(handle)
    orchestrator = CollectorsOrchestrator()
    orchestrator.run_all(handle, writer, EvidenceIDGenerator(handle.run_id))

    manifest = json.loads(handle.manifest_path.read_text())
    assert manifest["counts"]["findings"] >= 3
    assert manifest["counts"]["coverage_components"] >= 1
    assert manifest["tools"]["git-churn"]["executed"] is True
