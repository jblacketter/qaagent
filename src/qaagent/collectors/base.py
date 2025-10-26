"""Shared collector interfaces and result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from qaagent.evidence.models import ToolStatus


@dataclass
class CollectorResult:
    """Normalized output from a collector run."""

    tool_name: str
    version: Optional[str] = None
    exit_code: Optional[int] = None
    executed: bool = False
    findings: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None

    def mark_finished(self) -> None:
        self.finished_at = datetime.now(timezone.utc)

    def to_tool_status(self) -> ToolStatus:
        return ToolStatus(
            version=self.version,
            executed=self.executed,
            exit_code=self.exit_code,
            error="; ".join(self.errors) if self.errors else None,
        )
