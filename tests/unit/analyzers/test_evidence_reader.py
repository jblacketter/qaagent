from __future__ import annotations

import json
from pathlib import Path

import pytest

from qaagent.analyzers.evidence_reader import EvidenceReader
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator, FindingRecord
from qaagent.evidence.run_manager import RunManager


def _write_quality(writer: EvidenceWriter, id_generator: EvidenceIDGenerator) -> None:
    records = [
        FindingRecord(
            evidence_id=id_generator.next_id("fnd"),
            tool="flake8",
            severity="warning",
            code="E302",
            message="expected 2 blank lines, found 1",
            file="src/style.py",
            line=10,
            column=1,
            tags=["lint"],
        ).to_dict()
    ]
    writer.write_records("quality", records)


def _write_coverage(writer: EvidenceWriter, id_generator: EvidenceIDGenerator) -> None:
    writer.write_records(
        "coverage",
        [
            {
                "coverage_id": id_generator.next_id("cov"),
                "type": "line",
                "component": "src/style.py",
                "value": 0.5,
                "total_statements": 10,
                "covered_statements": 5,
                "sources": ["coverage.xml"],
            }
        ],
    )


def _write_churn(writer: EvidenceWriter, id_generator: EvidenceIDGenerator) -> None:
    writer.write_records(
        "churn",
        [
            {
                "evidence_id": id_generator.next_id("chn"),
                "path": "src/style.py",
                "window": "90d",
                "commits": 3,
                "lines_added": 20,
                "lines_deleted": 5,
                "contributors": 2,
            }
        ],
    )


def test_evidence_reader_reads_records(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("repo", repo)
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)

    _write_quality(writer, id_gen)
    _write_coverage(writer, id_gen)
    _write_churn(writer, id_gen)

    reader = EvidenceReader(handle)

    findings = reader.read_findings()
    assert len(findings) == 1
    assert findings[0].code == "E302"

    coverage = reader.read_coverage()
    assert len(coverage) == 1
    assert coverage[0].component == "src/style.py"

    churn = reader.read_churn()
    assert len(churn) == 1
    assert churn[0].commits == 3

    manifest = reader.read_manifest()
    assert manifest.run_id == handle.run_id


def test_evidence_reader_handles_missing_files(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("repo", repo)
    reader = EvidenceReader(handle)

    assert reader.read_findings() == []
    assert reader.read_coverage() == []
    assert reader.read_churn() == []


def test_evidence_reader_from_run_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("repo", repo)
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)
    _write_quality(writer, id_gen)

    reader = EvidenceReader.from_run_path(handle.run_dir, runs_root=tmp_path / "runs")
    assert reader.read_findings()
