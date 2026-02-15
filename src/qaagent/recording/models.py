"""Data models for browser recording and export."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SelectorCandidate:
    """Candidate selector with deterministic score ordering."""

    strategy: str
    value: str
    score: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecordedAction:
    """Normalized action captured during recording."""

    index: int
    action: str
    timestamp: float
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecordedFlow:
    """Recorded browser flow with normalized actions."""

    name: str
    start_url: str
    actions: List[RecordedAction] = field(default_factory=list)
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["actions"] = [action.to_dict() for action in self.actions]
        return payload

