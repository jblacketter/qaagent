from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from qaagent.collectors.bandit import BanditCollector
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager


@pytest.mark.skipif(shutil.which("bandit") is None, reason="bandit not installed")
def test_bandit_collector_discovers_security_findings(tmp_path: Path) -> None:
    fixtures = Path(__file__).parents[2] / "fixtures" / "synthetic_repo"
    repo_path = tmp_path / "synthetic_repo"
    shutil.copytree(fixtures, repo_path)

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("synthetic", repo_path)

    writer = EvidenceWriter(handle)
    collector = BanditCollector()
    result = collector.run(handle, writer, EvidenceIDGenerator(handle.run_id))

    assert result.executed is True
    assert any(f.code == "B101" for f in result.findings)

    quality_file = handle.evidence_dir / "quality.jsonl"
    payloads = [json.loads(line) for line in quality_file.read_text().strip().splitlines()]
    assert any(item["tool"] == "bandit" for item in payloads)

    artifact = handle.artifacts_dir / "bandit.json"
    assert artifact.exists()

    manifest = json.loads(handle.manifest_path.read_text())
    assert "bandit" in manifest["tools"]
