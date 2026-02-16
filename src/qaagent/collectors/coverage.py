"""Collector for test coverage artifacts (coverage.xml / lcov.info)."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qaagent.evidence import CoverageRecord, EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunHandle

from .base import CollectorResult

LOGGER = logging.getLogger(__name__)


@dataclass
class CoverageConfig:
    xml_path: str = "coverage.xml"
    lcov_path: str = "lcov.info"


class CoverageCollector:
    """Load coverage reports and normalize them to coverage records."""

    def __init__(self, config: Optional[CoverageConfig] = None) -> None:
        self.config = config or CoverageConfig()

    def run(
        self,
        handle: RunHandle,
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> CollectorResult:
        result = CollectorResult(tool_name="coverage")
        root_path = Path(handle.manifest.target.path)

        xml_file = root_path / self.config.xml_path
        lcov_file = root_path / self.config.lcov_path

        records: List[CoverageRecord] = []
        if xml_file.exists():
            LOGGER.info("Parsing coverage XML at %s", xml_file)
            try:
                records.extend(self._parse_coverage_xml(xml_file, id_generator, root_path))
            except Exception as exc:  # pragma: no cover - defensive
                msg = f"Failed to parse coverage XML: {exc}"
                LOGGER.error(msg)
                result.errors.append(msg)
        elif lcov_file.exists():
            LOGGER.info("Parsing LCOV report at %s", lcov_file)
            try:
                records.extend(self._parse_lcov(lcov_file, id_generator))
            except Exception as exc:  # pragma: no cover - defensive
                msg = f"Failed to parse LCOV: {exc}"
                LOGGER.error(msg)
                result.errors.append(msg)
        else:
            msg = "No coverage artifacts found (expecting coverage.xml or lcov.info)"
            LOGGER.info(msg)
            result.diagnostics.append(msg)

        if records:
            writer.write_records("coverage", [record.to_dict() for record in records])
            result.executed = True
            result.findings.extend([record.to_dict() for record in records])
        else:
            result.executed = False

        result.mark_finished()
        handle.register_tool("coverage", result.to_tool_status())
        handle.write_manifest()
        return result

    def _parse_coverage_xml(
        self, xml_path: Path, id_generator: EvidenceIDGenerator, repo_root: Path
    ) -> List[CoverageRecord]:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        records: List[CoverageRecord] = []
        sources = [elem.text for elem in root.findall("./sources/source") if elem.text]

        # Overall coverage
        line_rate = float(root.attrib.get("line-rate", 0.0))
        lines_valid = int(float(root.attrib.get("lines-valid", 0)))
        lines_covered = int(float(root.attrib.get("lines-covered", 0)))
        records.append(
            CoverageRecord(
                coverage_id=id_generator.next_id("cov"),
                type="line",
                component="__overall__",
                value=line_rate,
                total_statements=lines_valid or None,
                covered_statements=lines_covered or None,
                sources=[str(xml_path)],
                metadata={},
            )
        )

        for package in root.findall(".//package"):
            for klass in package.findall("classes/class"):
                filename = klass.attrib.get("filename")
                if not filename:
                    continue
                class_line_rate = float(klass.attrib.get("line-rate", 0.0))
                lines = klass.findall("lines/line")
                total = len(lines)
                covered = sum(1 for line in lines if int(line.attrib.get("hits", "0")) > 0)
                component = self._resolve_component(filename, sources, repo_root)
                records.append(
                    CoverageRecord(
                        coverage_id=id_generator.next_id("cov"),
                        type="line",
                        component=component,
                        value=class_line_rate,
                        total_statements=total or None,
                        covered_statements=covered or None,
                        sources=[str(xml_path)],
                        metadata={},
                    )
                )
        return records

    def _parse_lcov(
        self, lcov_path: Path, id_generator: EvidenceIDGenerator
    ) -> List[CoverageRecord]:
        # Minimal LCOV parser (per-file line coverage)
        records: List[CoverageRecord] = []
        current_file: Optional[str] = None
        total = 0
        covered = 0
        with lcov_path.open(encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line.startswith("SF:"):
                    if current_file is not None:
                        value = (covered / total) if total else 0.0
                        records.append(
                            CoverageRecord(
                                coverage_id=id_generator.next_id("cov"),
                                type="line",
                                component=self._normalize_component(current_file),
                                value=value,
                                total_statements=total or None,
                                covered_statements=covered or None,
                                sources=[str(lcov_path)],
                                metadata={},
                            )
                        )
                    current_file = line[3:]
                    total = 0
                    covered = 0
                elif line.startswith("DA:"):
                    _, data = line.split(":", 1)
                    parts = data.split(",")
                    if len(parts) >= 2:
                        total += 1
                        hits = int(parts[1])
                        if hits > 0:
                            covered += 1
                elif line == "end_of_record" and current_file is not None:
                    value = (covered / total) if total else 0.0
                    records.append(
                        CoverageRecord(
                            coverage_id=id_generator.next_id("cov"),
                            type="line",
                            component=self._normalize_component(current_file),
                            value=value,
                            total_statements=total or None,
                            covered_statements=covered or None,
                            sources=[str(lcov_path)],
                            metadata={},
                        )
                    )
                    current_file = None
                    total = 0
                    covered = 0
        return records

    def _resolve_component(self, filename: str, sources: List[str], repo_root: Path) -> str:
        candidate = Path(filename)
        if candidate.is_absolute():
            try:
                return self._normalize_component(candidate.relative_to(repo_root))
            except ValueError:
                return self._normalize_component(candidate)
        for source in sources:
            try:
                combined = Path(source) / filename
                if combined.exists():
                    try:
                        return self._normalize_component(combined.relative_to(repo_root))
                    except ValueError:
                        return self._normalize_component(combined)
            except Exception:  # pragma: no cover - defensive
                continue
        return self._normalize_component(Path(repo_root / filename).relative_to(repo_root))

    @staticmethod
    def _normalize_component(path: Path | str) -> str:
        return str(path).replace("\\", "/")
