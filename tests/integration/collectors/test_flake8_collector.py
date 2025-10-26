from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from qaagent.collectors.flake8 import Flake8Collector
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager


@pytest.mark.skipif(shutil.which("flake8") is None, reason="flake8 not installed")
def test_flake8_collector_discovers_expected_findings(tmp_path: Path) -> None:
    fixtures = Path(__file__).parents[2] / "fixtures" / "synthetic_repo"
    repo_path = tmp_path / "synthetic_repo"
    shutil.copytree(fixtures, repo_path)

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("synthetic", repo_path)

    writer = EvidenceWriter(handle)
    collector = Flake8Collector()
    result = collector.run(handle, writer, EvidenceIDGenerator(handle.run_id))

    assert result.executed is True
    assert result.exit_code == 1  # lint violations produce exit code 1
    e302 = [f for f in result.findings if f.code == "E302"]
    assert len(e302) == 3

    quality_file = handle.evidence_dir / "quality.jsonl"
    assert quality_file.exists()
    payloads = [json.loads(line) for line in quality_file.read_text().strip().splitlines()]
    assert sum(1 for item in payloads if item["code"] == "E302") == 3
    assert all(item["tool"] == "flake8" for item in payloads)
    assert all(item["evidence_id"].startswith("FND-") for item in payloads)

    # Manifest counts and tool status updated
    manifest = json.loads(handle.manifest_path.read_text())
    assert manifest["counts"]["findings"] == len(payloads)
    assert manifest["counts"]["findings"] >= 3
    assert manifest["tools"]["flake8"]["executed"] is True
