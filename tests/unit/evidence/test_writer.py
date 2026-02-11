"""Tests for EvidenceWriter and JsonlWriter."""
from __future__ import annotations

import json
from pathlib import Path

from qaagent.evidence.run_manager import RunManager
from qaagent.evidence.writer import EvidenceWriter, JsonlWriter


class TestJsonlWriter:
    def test_append_writes_records(self, tmp_path: Path):
        """Test appending records to a JSONL file."""
        path = tmp_path / "output.jsonl"
        writer = JsonlWriter(path)

        records = [{"id": 1, "msg": "hello"}, {"id": 2, "msg": "world"}]
        count = writer.append(records)

        assert count == 2
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == 1
        assert json.loads(lines[1])["msg"] == "world"

    def test_append_returns_zero_for_empty(self, tmp_path: Path):
        """Test appending empty iterable returns 0."""
        path = tmp_path / "output.jsonl"
        writer = JsonlWriter(path)

        count = writer.append([])

        assert count == 0

    def test_append_creates_parent_dirs(self, tmp_path: Path):
        """Test that parent directories are created."""
        path = tmp_path / "nested" / "deep" / "output.jsonl"
        writer = JsonlWriter(path)

        writer.append([{"x": 1}])

        assert path.exists()

    def test_append_is_additive(self, tmp_path: Path):
        """Test that multiple appends accumulate."""
        path = tmp_path / "output.jsonl"
        writer = JsonlWriter(path)

        writer.append([{"batch": 1}])
        writer.append([{"batch": 2}, {"batch": 3}])

        lines = path.read_text().strip().splitlines()
        assert len(lines) == 3


class TestEvidenceWriter:
    def _make_handle(self, tmp_path: Path):
        """Helper to create a RunHandle for testing."""
        base_dir = tmp_path / "runs"
        target_path = tmp_path / "repo"
        target_path.mkdir()
        manager = RunManager(base_dir=base_dir)
        return manager.create_run("test-target", target_path)

    def test_write_records_creates_jsonl(self, tmp_path: Path):
        """Test writing records creates the JSONL file."""
        handle = self._make_handle(tmp_path)
        writer = EvidenceWriter(handle)

        records = [{"evidence_id": "FND-001", "tool": "test", "message": "issue"}]
        count = writer.write_records("quality", records)

        assert count == 1
        evidence_path = handle.evidence_dir / "quality.jsonl"
        assert evidence_path.exists()
        lines = evidence_path.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_write_records_updates_manifest_counts(self, tmp_path: Path):
        """Test that manifest counts are updated for mapped record types."""
        handle = self._make_handle(tmp_path)
        writer = EvidenceWriter(handle)

        records = [{"id": "R-001"}, {"id": "R-002"}]
        writer.write_records("risks", records)

        manifest = json.loads(handle.manifest_path.read_text())
        assert manifest["counts"]["risks"] == 2

    def test_write_records_zero_records(self, tmp_path: Path):
        """Test writing zero records returns 0 and doesn't update manifest."""
        handle = self._make_handle(tmp_path)
        writer = EvidenceWriter(handle)

        count = writer.write_records("quality", [])

        assert count == 0

    def test_write_record_single(self, tmp_path: Path):
        """Test write_record convenience method."""
        handle = self._make_handle(tmp_path)
        writer = EvidenceWriter(handle)

        writer.write_record("findings", {"id": "F-001", "msg": "test finding"})

        evidence_path = handle.evidence_dir / "findings.jsonl"
        lines = evidence_path.read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == "F-001"

    def test_write_records_unmapped_type(self, tmp_path: Path):
        """Test writing records with a type not in COUNT_MAPPING."""
        handle = self._make_handle(tmp_path)
        writer = EvidenceWriter(handle)

        count = writer.write_records("custom_type", [{"data": "value"}])

        assert count == 1
        evidence_path = handle.evidence_dir / "custom_type.jsonl"
        assert evidence_path.exists()

    def test_write_records_reuses_writer(self, tmp_path: Path):
        """Test that the same JsonlWriter is reused for a record type."""
        handle = self._make_handle(tmp_path)
        writer = EvidenceWriter(handle)

        writer.write_records("quality", [{"id": 1}])
        writer.write_records("quality", [{"id": 2}])

        evidence_path = handle.evidence_dir / "quality.jsonl"
        lines = evidence_path.read_text().strip().splitlines()
        assert len(lines) == 2
