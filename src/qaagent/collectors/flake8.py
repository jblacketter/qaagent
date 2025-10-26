"""Collector for flake8 lint findings."""

from __future__ import annotations

import logging
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator, FindingRecord
from qaagent.evidence.run_manager import RunHandle

from .base import CollectorResult

LOGGER = logging.getLogger(__name__)


_FLAKE8_PATTERN = re.compile(
    r"^(?P<file>.*?):(?P<line>\d+):(?P<column>\d+):\s(?P<code>[A-Z]\d{3})\s(?P<message>.*)$"
)


@dataclass
class Flake8Config:
    """Configuration for running the flake8 collector."""

    executable: str = "flake8"
    extra_args: Optional[List[str]] = None
    timeout: int = 120


class Flake8Collector:
    """Run flake8, parse default output, and normalize findings."""

    def __init__(self, config: Optional[Flake8Config] = None) -> None:
        self.config = config or Flake8Config()

    def run(
        self,
        handle: RunHandle,
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> CollectorResult:
        result = CollectorResult(tool_name="flake8")
        result.version = self._detect_version()

        cmd = self._build_command()
        LOGGER.info("Running flake8: %s", " ".join(shlex.quote(part) for part in cmd))

        try:
            completed = subprocess.run(
                cmd,
                cwd=self._target_path(handle),
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
            )
        except FileNotFoundError:
            msg = f"flake8 executable not found: {self.config.executable}"
            LOGGER.warning(msg)
            result.diagnostics.append(msg)
            result.mark_finished()
            handle.register_tool("flake8", result.to_tool_status())
            handle.write_manifest()
            return result
        except subprocess.TimeoutExpired:
            msg = f"flake8 timed out after {self.config.timeout} seconds"
            LOGGER.error(msg)
            result.errors.append(msg)
            result.mark_finished()
            handle.register_tool("flake8", result.to_tool_status())
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
            else:
                result.errors.append("flake8 failed")

        findings = self._parse_output(stdout, id_generator)
        result.findings.extend(findings)
        if findings:
            writer.write_records("quality", [finding.to_dict() for finding in findings])

        result.mark_finished()
        handle.register_tool("flake8", result.to_tool_status())
        handle.write_manifest()
        return result

    def _target_path(self, handle: RunHandle) -> Path:
        return Path(handle.manifest.target.path)

    def _build_command(self) -> List[str]:
        args = [self.config.executable]
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
        artifact = handle.artifacts_dir / "flake8.log"
        artifact.write_text(stdout if stdout.endswith("\n") else stdout + "\n", encoding="utf-8")

    def _parse_output(
        self, output: str, id_generator: EvidenceIDGenerator
    ) -> List[FindingRecord]:
        findings: List[FindingRecord] = []
        if not output:
            return findings

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            match = _FLAKE8_PATTERN.match(line)
            if not match:
                LOGGER.debug("Unrecognized flake8 line: %s", line)
                continue
            groups = match.groupdict()
            file_path = groups.get("file") or ""
            if file_path.startswith("./"):
                file_path = file_path[2:]
            findings.append(
                FindingRecord(
                    evidence_id=id_generator.next_id("fnd"),
                    tool="flake8",
                    severity="warning",
                    code=groups.get("code"),
                    message=groups.get("message", ""),
                    file=file_path,
                    line=int(groups["line"]),
                    column=int(groups["column"]),
                    tags=["lint"],
                    metadata={"raw": line},
                )
            )

        return findings
