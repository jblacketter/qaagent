from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from qaagent.collectors.pylint import PylintCollector
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager


@pytest.mark.skipif(shutil.which("pylint") is None, reason="pylint not installed")
def test_pylint_collector_discovers_findings(tmp_path: Path) -> None:
    fixtures = Path(__file__).parents[2] / "fixtures" / "synthetic_repo"
    repo_path = tmp_path / "synthetic_repo"
    shutil.copytree(fixtures, repo_path)

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("synthetic", repo_path)

    writer = EvidenceWriter(handle)
    collector = PylintCollector()
    result = collector.run(handle, writer, EvidenceIDGenerator(handle.run_id))

    assert result.executed is True
    assert result.findings, "Expected pylint to report findings"

    quality_file = handle.evidence_dir / "quality.jsonl"
    assert quality_file.exists()
    payloads = [json.loads(line) for line in quality_file.read_text().strip().splitlines()]
    assert any(item["tool"] == "pylint" for item in payloads)

    artifact = handle.artifacts_dir / "pylint.json"
    assert artifact.exists()

    manifest = json.loads(handle.manifest_path.read_text())
    assert "pylint" in manifest["tools"]
