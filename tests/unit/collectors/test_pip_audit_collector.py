from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import subprocess

import pytest

from qaagent.collectors.pip_audit import PipAuditCollector, PipAuditConfig
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunManager


class DummyCompletedProcess:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = "") -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def test_pip_audit_collector_parses_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    requirements = repo / "requirements.txt"
    requirements.write_text("django==2.2.0\n", encoding="utf-8")

    manager = RunManager(base_dir=tmp_path / "runs")
    handle = manager.create_run("synthetic", repo)
    writer = EvidenceWriter(handle)

    sample_output = json.dumps(
        [
            {
                "name": "django",
                "version": "2.2.0",
                "vulns": [
                    {
                        "id": "CVE-2019-12781",
                        "description": "Sample vulnerability",
                        "fix_versions": ["2.2.4"],
                    }
                ],
            }
        ]
    )

    def fake_run(*args, **kwargs):
        stdout = sample_output
        return DummyCompletedProcess(stdout=stdout, returncode=1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    collector = PipAuditCollector(PipAuditConfig())
    result = collector.run(handle, writer, EvidenceIDGenerator(handle.run_id))

    assert result.executed is True
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "CVE-2019-12781"
    assert finding.metadata["package"] == "django"

    quality_path = handle.evidence_dir / "quality.jsonl"
    contents = quality_path.read_text().strip().splitlines()
    assert len(contents) == 1
    payload = json.loads(contents[0])
    assert payload["code"] == "CVE-2019-12781"
