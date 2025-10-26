from __future__ import annotations

import json
from pathlib import Path

from qaagent.evidence.run_manager import RunManager
from qaagent.evidence.writer import EvidenceWriter


def test_create_run_creates_directories_and_manifest(tmp_path: Path) -> None:
    base_dir = tmp_path / "runs"
    target_path = tmp_path / "repo"
    target_path.mkdir()

    manager = RunManager(base_dir=base_dir)
    handle = manager.create_run("synthetic", target_path, git_metadata={"commit": "abc123"})

    assert handle.run_dir.exists()
    assert handle.evidence_dir.exists()
    assert handle.artifacts_dir.exists()
    manifest_data = json.loads(handle.manifest_path.read_text())
    assert manifest_data["run_id"] == handle.run_id
    assert manifest_data["target"]["name"] == "synthetic"
    assert manifest_data["target"]["git"]["commit"] == "abc123"
    assert manifest_data["counts"]["findings"] == 0


def test_create_run_generates_unique_run_ids(tmp_path: Path) -> None:
    base_dir = tmp_path / "runs"
    target_path = tmp_path / "repo"
    target_path.mkdir()
    manager = RunManager(base_dir=base_dir)

    handle_one = manager.create_run("synthetic", target_path)
    handle_two = manager.create_run("synthetic", target_path)

    assert handle_one.run_id != handle_two.run_id


def test_evidence_writer_updates_manifest_counts(tmp_path: Path) -> None:
    base_dir = tmp_path / "runs"
    target_path = tmp_path / "repo"
    target_path.mkdir()
    manager = RunManager(base_dir=base_dir)
    handle = manager.create_run("synthetic", target_path)

    writer = EvidenceWriter(handle)
    records = [
        {
            "evidence_id": "FND-001",
            "tool": "flake8",
            "severity": "warning",
            "code": "E302",
            "message": "expected 2 blank lines, found 1",
            "file": "src/style_issues.py",
            "line": 10,
            "column": 1,
        },
        {
            "evidence_id": "FND-002",
            "tool": "flake8",
            "severity": "warning",
            "code": "E302",
            "message": "expected 2 blank lines, found 1",
            "file": "src/style_issues.py",
            "line": 20,
            "column": 1,
        },
    ]
    writer.write_records("quality", records)

    manifest_data = json.loads(handle.manifest_path.read_text())
    assert manifest_data["counts"]["findings"] == 2
    assert manifest_data["evidence_files"]["quality"].startswith("evidence/")
    evidence_path = handle.evidence_dir / "quality.jsonl"
    lines = evidence_path.read_text().strip().splitlines()
    assert len(lines) == 2
