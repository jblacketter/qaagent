from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from qaagent.collectors.coverage import CoverageCollector
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager


def test_coverage_collector_parses_coverage_xml(tmp_path: Path) -> None:
    fixtures = Path(__file__).parents[2] / "fixtures" / "synthetic_repo"
    repo_path = tmp_path / "synthetic_repo"
    shutil.copytree(fixtures, repo_path)

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("synthetic", repo_path)

    writer = EvidenceWriter(handle)
    collector = CoverageCollector()
    result = collector.run(handle, writer, EvidenceIDGenerator(handle.run_id))

    assert result.executed is True

    coverage_file = handle.evidence_dir / "coverage.jsonl"
    payloads = [json.loads(line) for line in coverage_file.read_text().strip().splitlines()]
    assert any(item["component"] == "__overall__" for item in payloads)
    assert any(item["component"].endswith("auth/session.py") for item in payloads)

    manifest = json.loads(handle.manifest_path.read_text())
    assert manifest["counts"]["coverage_components"] >= len(payloads)
    assert "coverage" in manifest["tools"]
