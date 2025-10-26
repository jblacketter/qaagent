"""Collector for pylint diagnostics."""

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
class PylintConfig:
    executable: str = "pylint"
    extra_args: Optional[List[str]] = None
    timeout: int = 180


class PylintCollector:
    """Run pylint in JSON mode and normalize output."""

    def __init__(self, config: Optional[PylintConfig] = None) -> None:
        self.config = config or PylintConfig()

    def run(
        self,
        handle: RunHandle,
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> CollectorResult:
        result = CollectorResult(tool_name="pylint")
        result.version = self._detect_version()

        cmd = self._build_command()
        LOGGER.info("Running pylint: %s", " ".join(shlex.quote(part) for part in cmd))

        try:
            completed = subprocess.run(
                cmd,
                cwd=self._target_path(handle),
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
            )
        except FileNotFoundError:
            msg = f"pylint executable not found: {self.config.executable}"
            LOGGER.warning(msg)
            result.diagnostics.append(msg)
            result.mark_finished()
            handle.register_tool("pylint", result.to_tool_status())
            handle.write_manifest()
            return result
        except subprocess.TimeoutExpired:
            msg = f"pylint timed out after {self.config.timeout} seconds"
            LOGGER.error(msg)
            result.errors.append(msg)
            result.mark_finished()
            handle.register_tool("pylint", result.to_tool_status())
            handle.write_manifest()
            return result

        result.executed = True
        result.exit_code = completed.returncode
        stdout = completed.stdout.strip()
        if stdout:
            self._write_artifact(handle, stdout)

        if completed.returncode not in (0, 32):  # pylint returns 32 on lint failures
            stderr = completed.stderr.strip()
            if stderr:
                result.errors.append(stderr)

        findings = self._parse_output(stdout, id_generator)
        result.findings.extend(findings)
        if findings:
            writer.write_records("quality", [finding.to_dict() for finding in findings])

        result.mark_finished()
        handle.register_tool("pylint", result.to_tool_status())
        handle.write_manifest()
        return result

    def _target_path(self, handle: RunHandle) -> Path:
        return Path(handle.manifest.target.path)

    def _build_command(self) -> List[str]:
        args = [self.config.executable, "--output-format=json"]
        if self.config.extra_args:
            args.extend(self.config.extra_args)
        else:
            args.append(self._default_target())
        return args

    def _default_target(self) -> str:
        return "src"
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
        artifact = handle.artifacts_dir / "pylint.json"
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
            LOGGER.error("Unable to parse pylint JSON output")
            return findings

        if not isinstance(data, list):
            LOGGER.debug("Unexpected pylint payload: %s", type(data))
            return findings

        for item in data:
            if not isinstance(item, dict):
                continue
            code = item.get("symbol") or item.get("message-id")
            findings.append(
                FindingRecord(
                    evidence_id=id_generator.next_id("fnd"),
                    tool="pylint",
                    severity=item.get("type", "warning"),
                    code=code,
                    message=item.get("message", ""),
                    file=item.get("path"),
                    line=item.get("line"),
                    column=item.get("column"),
                    tags=["lint", "pylint"],
                    metadata={"obj": item.get("obj")},
                )
            )
        return findings
