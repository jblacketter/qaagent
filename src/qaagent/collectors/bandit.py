"""Collector for Bandit security findings."""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator, FindingRecord
from qaagent.evidence.run_manager import RunHandle

from .base import CollectorResult

LOGGER = logging.getLogger(__name__)


@dataclass
class BanditConfig:
    executable: str = "bandit"
    target: str = "."
    extra_args: Optional[List[str]] = None
    timeout: int = 180


class BanditCollector:
    """Run Bandit security scanner and normalize results."""

    def __init__(self, config: Optional[BanditConfig] = None) -> None:
        self.config = config or BanditConfig()

    def run(
        self,
        handle: RunHandle,
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> CollectorResult:
        result = CollectorResult(tool_name="bandit")
        result.version = self._detect_version()

        cmd = self._build_command()
        LOGGER.info("Running bandit: %s", " ".join(shlex.quote(part) for part in cmd))

        try:
            completed = subprocess.run(
                cmd,
                cwd=self._target_path(handle),
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
            )
        except FileNotFoundError:
            msg = f"bandit executable not found: {self.config.executable}"
            LOGGER.warning(msg)
            result.diagnostics.append(msg)
            result.mark_finished()
            handle.register_tool("bandit", result.to_tool_status())
            handle.write_manifest()
            return result
        except subprocess.TimeoutExpired:
            msg = f"bandit timed out after {self.config.timeout} seconds"
            LOGGER.error(msg)
            result.errors.append(msg)
            result.mark_finished()
            handle.register_tool("bandit", result.to_tool_status())
            handle.write_manifest()
            return result

        result.executed = True
        result.exit_code = completed.returncode
        stdout = completed.stdout.strip()
        if stdout:
            self._write_artifact(handle, stdout)

        if completed.returncode not in (0, 1):
            stderr = completed.stderr.strip()
            if stderr:
                result.errors.append(stderr)

        findings = self._parse_output(stdout, id_generator)
        result.findings.extend(findings)
        if findings:
            writer.write_records("quality", [finding.to_dict() for finding in findings])

        result.mark_finished()
        handle.register_tool("bandit", result.to_tool_status())
        handle.write_manifest()
        return result

    def _target_path(self, handle: RunHandle) -> Path:
        return Path(handle.manifest.target.path)

    def _build_command(self) -> List[str]:
        args = [self.config.executable, "-f", "json", "-q", "-r", self.config.target]
        if self.config.extra_args:
            args.extend(self.config.extra_args)
        return args

    def _detect_version(self) -> Optional[str]:
        try:
            proc = subprocess.run(
                [self.config.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        tokens = (proc.stdout.strip() or proc.stderr.strip()).split()
        return tokens[0] if tokens else None

    def _write_artifact(self, handle: RunHandle, stdout: str) -> None:
        artifact = handle.artifacts_dir / "bandit.json"
        artifact.write_text(stdout if stdout.endswith("\n") else stdout + "\n", encoding="utf-8")

    def _parse_output(
        self, output: str, id_generator: EvidenceIDGenerator
    ) -> List[FindingRecord]:
        findings: List[FindingRecord] = []
        if not output:
            return findings
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            LOGGER.error("Unable to parse bandit JSON output")
            return findings

        results = data.get("results", []) if isinstance(data, dict) else []
        for item in results:
            if not isinstance(item, dict):
                continue
            severity = (item.get("issue_severity") or "medium").lower()
            confidence = item.get("issue_confidence")
            findings.append(
                FindingRecord(
                    evidence_id=id_generator.next_id("fnd"),
                    tool="bandit",
                    severity=severity,
                    code=item.get("test_id"),
                    message=item.get("issue_text", ""),
                    file=item.get("filename"),
                    line=item.get("line_number"),
                    column=None,
                    tags=["security", "bandit"],
                    confidence=_confidence_to_float(confidence),
                    metadata={
                        "confidence": confidence,
                        "cwe": item.get("cwe"),
                    },
                )
            )
        return findings


def _confidence_to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    mapping = {"low": 0.3, "medium": 0.6, "high": 0.9}
    return mapping.get(str(value).lower())
