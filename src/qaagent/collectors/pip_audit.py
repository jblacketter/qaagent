"""Collector for dependency vulnerabilities using pip-audit."""

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
class PipAuditConfig:
    executable: str = "pip-audit"
    timeout: int = 180
    extra_args: Optional[List[str]] = None


class PipAuditCollector:
    """Run pip-audit and normalize vulnerability findings."""

    def __init__(self, config: Optional[PipAuditConfig] = None) -> None:
        self.config = config or PipAuditConfig()

    def run(
        self,
        handle: RunHandle,
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> CollectorResult:
        result = CollectorResult(tool_name="pip-audit")
        result.version = self._detect_version()

        manifests = self._discover_manifests(handle)
        if not manifests:
            msg = "No requirements files found for pip-audit"
            LOGGER.info(msg)
            result.diagnostics.append(msg)
            result.mark_finished()
            handle.register_tool("pip-audit", result.to_tool_status())
            handle.write_manifest()
            return result

        findings: List[FindingRecord] = []
        for manifest in manifests:
            cmd = self._build_command(manifest)
            LOGGER.info(
                "Running pip-audit: %s",
                " ".join(shlex.quote(part) for part in cmd),
            )
            try:
                completed = subprocess.run(
                    cmd,
                    cwd=self._target_path(handle),
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout,
                )
            except FileNotFoundError:
                msg = f"pip-audit executable not found: {self.config.executable}"
                LOGGER.warning(msg)
                result.diagnostics.append(msg)
                result.mark_finished()
                handle.register_tool("pip-audit", result.to_tool_status())
                handle.write_manifest()
                return result
            except subprocess.TimeoutExpired:
                msg = f"pip-audit timed out after {self.config.timeout} seconds"
                LOGGER.error(msg)
                result.errors.append(msg)
                continue

            stdout = completed.stdout.strip()
            if stdout:
                self._write_artifact(handle, stdout, manifest)

            if completed.returncode not in (0, 1):
                stderr = completed.stderr.strip()
                if stderr:
                    result.errors.append(stderr)

            parsed = self._parse_output(stdout, id_generator, manifest)
            findings.extend(parsed)

        result.executed = bool(findings or not result.errors)
        result.findings.extend(findings)
        if findings:
            writer.write_records("quality", [finding.to_dict() for finding in findings])

        result.mark_finished()
        handle.register_tool("pip-audit", result.to_tool_status())
        handle.write_manifest()
        return result

    def _target_path(self, handle: RunHandle) -> Path:
        return Path(handle.manifest.target.path)

    def _discover_manifests(self, handle: RunHandle) -> List[str]:
        root = self._target_path(handle)
        patterns = ["requirements.txt"] + [
            str(p.relative_to(root))
            for p in root.glob("requirements*.txt")
            if p.name != "requirements.txt"
        ]
        manifests = []
        for pattern in patterns:
            manifest_path = root / pattern
            if manifest_path.exists():
                manifests.append(pattern)
        return sorted(set(manifests))

    def _build_command(self, manifest: str) -> List[str]:
        args = [self.config.executable, "-r", manifest, "--format", "json"]
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

    def _write_artifact(self, handle: RunHandle, stdout: str, manifest: str) -> None:
        safe_manifest = manifest.replace("/", "_")
        artifact = handle.artifacts_dir / f"pip_audit_{safe_manifest}.json"
        artifact.write_text(stdout if stdout.endswith("\n") else stdout + "\n", encoding="utf-8")

    def _parse_output(
        self, output: str, id_generator: EvidenceIDGenerator, manifest: str
    ) -> List[FindingRecord]:
        findings: List[FindingRecord] = []
        if not output:
            return findings
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            LOGGER.error("Unable to parse pip-audit JSON output for %s", manifest)
            return findings

        if not isinstance(data, list):
            LOGGER.debug("Unexpected pip-audit payload type: %s", type(data))
            return findings

        for entry in data:
            if not isinstance(entry, dict):
                continue
            vulnerabilities = entry.get("vulns") or []
            for vuln in vulnerabilities:
                findings.append(
                    FindingRecord(
                        evidence_id=id_generator.next_id("fnd"),
                        tool="pip-audit",
                        severity="critical" if vuln.get("fix_versions") else "high",
                        code=vuln.get("id"),
                        message=vuln.get("description", ""),
                        file=manifest,
                        line=None,
                        column=None,
                        tags=["dependency", "security"],
                        metadata={
                            "package": entry.get("name"),
                            "installed": entry.get("version"),
                            "fix_versions": vuln.get("fix_versions"),
                        },
                    )
                )
        return findings
