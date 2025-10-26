"""Utilities for creating and managing evidence store runs."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Union

from .models import Manifest, TargetMetadata, ToolStatus

LOGGER = logging.getLogger(__name__)

_RUN_TIMESTAMP = "%Y%m%d_%H%M%SZ"


@dataclass
class RunHandle:
    """Represents an active run directory and manifest context."""

    run_id: str
    run_dir: Path
    evidence_dir: Path
    artifacts_dir: Path
    manifest: Manifest

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "manifest.json"

    def write_manifest(self) -> None:
        """Persist the manifest to disk."""
        self.manifest_path.write_text(json.dumps(self.manifest.to_dict(), indent=2), encoding="utf-8")

    def register_evidence_file(self, record_type: str, path: Path) -> None:
        relative = path.relative_to(self.run_dir)
        self.manifest.register_file(record_type, relative.as_posix())

    def increment_count(self, key: str, amount: int) -> None:
        self.manifest.increment_count(key, amount)

    def register_tool(self, name: str, status: ToolStatus) -> None:
        self.manifest.register_tool(name, status)

    def add_diagnostic(self, message: str) -> None:
        self.manifest.add_diagnostic(message)

    def finalize(self) -> None:
        """Write manifest to disk (alias for clarity)."""
        self.write_manifest()


class RunManager:
    """Creates run directories beneath the qaagent runs root."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        env_dir = os.getenv("QAAGENT_RUNS_DIR")
        if base_dir is not None:
            runs_root = base_dir
        elif env_dir:
            runs_root = Path(env_dir).expanduser()
        else:
            runs_root = Path.home() / ".qaagent" / "runs"
        self.base_dir = runs_root
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        target_name: str,
        target_path: Path,
        git_metadata: Optional[Dict[str, str]] = None,
    ) -> RunHandle:
        """Create a new run directory and manifest skeleton."""
        run_id = self._generate_run_id()
        run_dir = self.base_dir / run_id
        evidence_dir = run_dir / "evidence"
        artifacts_dir = run_dir / "artifacts"
        evidence_dir.mkdir(parents=True, exist_ok=False)
        artifacts_dir.mkdir(parents=True, exist_ok=False)

        manifest = Manifest(
            run_id=run_id,
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            target=TargetMetadata(name=target_name, path=str(target_path), git=git_metadata or {}),
        )

        handle = RunHandle(
            run_id=run_id,
            run_dir=run_dir,
            evidence_dir=evidence_dir,
            artifacts_dir=artifacts_dir,
            manifest=manifest,
        )

        self._log_retention_notice(run_dir)
        handle.write_manifest()
        return handle

    def load_run(self, run: Union[str, Path]) -> RunHandle:
        """Load an existing run from disk."""
        run_dir = self._resolve_run_path(run)
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in run directory: {manifest_path}")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = Manifest.from_dict(data)
        evidence_dir = run_dir / "evidence"
        artifacts_dir = run_dir / "artifacts"

        return RunHandle(
            run_id=manifest.run_id,
            run_dir=run_dir,
            evidence_dir=evidence_dir,
            artifacts_dir=artifacts_dir,
            manifest=manifest,
        )

    def _generate_run_id(self) -> str:
        base = datetime.now(timezone.utc).strftime(_RUN_TIMESTAMP)
        candidate = base
        counter = 1
        while (self.base_dir / candidate).exists():
            candidate = f"{base}_{counter:02d}"
            counter += 1
        return candidate

    def _resolve_run_path(self, run: Union[str, Path]) -> Path:
        if isinstance(run, Path):
            run_dir = run
        else:
            candidate = Path(run)
            if candidate.is_absolute():
                run_dir = candidate
            else:
                run_dir = self.base_dir / candidate

        if not run_dir.is_absolute():
            run_dir = (self.base_dir / run_dir).resolve()
        else:
            run_dir = run_dir.resolve()
        return run_dir

    def _log_retention_notice(self, run_dir: Path) -> None:
        LOGGER.info(
            "Created qaagent run directory at %s. Automatic pruning is not yet implemented; "
            "remember to clean up old runs manually.",
            run_dir,
        )
