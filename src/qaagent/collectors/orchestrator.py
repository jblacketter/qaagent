"""Orchestrate execution of collectors and persist evidence."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List

from qaagent.collectors.bandit import BanditCollector
from qaagent.collectors.coverage import CoverageCollector
from qaagent.collectors.flake8 import Flake8Collector
from qaagent.collectors.git_churn import GitChurnCollector
from qaagent.collectors.pip_audit import PipAuditCollector
from qaagent.collectors.pylint import PylintCollector
from qaagent.collectors.base import CollectorResult
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator
from qaagent.evidence.run_manager import RunHandle

LOGGER = logging.getLogger(__name__)


@dataclass
class CollectorEntry:
    name: str
    factory: Callable[[], object]


@dataclass
class CollectorsOrchestrator:
    """Run configured collectors sequentially for a run handle."""

    collectors: List[CollectorEntry] = field(
        default_factory=lambda: [
            CollectorEntry("flake8", Flake8Collector),
            CollectorEntry("pylint", PylintCollector),
            CollectorEntry("bandit", BanditCollector),
            CollectorEntry("pip-audit", PipAuditCollector),
            CollectorEntry("coverage", CoverageCollector),
            CollectorEntry("git-churn", GitChurnCollector),
        ]
    )

    def run_all(
        self,
        handle: RunHandle,
        writer: EvidenceWriter,
        id_generator: EvidenceIDGenerator,
    ) -> List[CollectorResult]:
        results: List[CollectorResult] = []
        log_path = self._log_path(handle)

        for entry in self.collectors:
            collector = entry.factory()
            LOGGER.info("Running collector: %s", entry.name)
            self._log_event(log_path, {"event": "collector.start", "collector": entry.name})
            run_result = collector.run(handle, writer, id_generator)  # type: ignore[arg-type]
            results.append(run_result)
            self._log_event(
                log_path,
                {
                    "event": "collector.finish",
                    "collector": entry.name,
                    "executed": run_result.executed,
                    "findings": len(getattr(run_result, "findings", [])),
                    "errors": run_result.errors,
                    "diagnostics": run_result.diagnostics,
                },
            )
        return results

    def _log_path(self, handle: RunHandle) -> Path:
        qa_home = handle.run_dir.parent.parent
        logs_dir = qa_home / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir / f"{handle.run_id}.jsonl"

    def _log_event(self, path: Path, payload: dict) -> None:
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload))
            fp.write("\n")
