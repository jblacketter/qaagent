"""Utilities for writing evidence records to JSONL files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Mapping, Dict

from .run_manager import RunHandle

LOGGER = logging.getLogger(__name__)

COUNT_MAPPING: Dict[str, str] = {
    "quality": "findings",
    "findings": "findings",
    "risks": "risks",
    "coverage": "coverage_components",
    "tests": "tests",
}


class JsonlWriter:
    """Lightweight helper to append JSON Lines records."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, records: Iterable[Mapping[str, object]]) -> int:
        count = 0
        with self.path.open("a", encoding="utf-8") as fp:
            for record in records:
                fp.write(json.dumps(record))
                fp.write("\n")
                count += 1
        return count


class EvidenceWriter:
    """Coordinates writing JSONL evidence files and manifest updates."""

    def __init__(self, handle: RunHandle) -> None:
        self.handle = handle
        self._writers: Dict[str, JsonlWriter] = {}

    def write_records(self, record_type: str, records: Iterable[Mapping[str, object]]) -> int:
        """Write records of a given type and update manifest counts."""
        path = self.handle.evidence_dir / f"{record_type}.jsonl"
        writer = self._writers.setdefault(record_type, JsonlWriter(path))
        count = writer.append(records)
        if count == 0:
            return 0

        self.handle.register_evidence_file(record_type, path)
        count_key = COUNT_MAPPING.get(record_type)
        if count_key:
            self.handle.increment_count(count_key, count)
        LOGGER.debug("Wrote %s %s records to %s", count, record_type, path)
        self.handle.write_manifest()
        return count

    def write_record(self, record_type: str, record: Mapping[str, object]) -> None:
        self.write_records(record_type, [record])
