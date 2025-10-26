"""Helpers for generating evidence IDs with deterministic formatting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class EvidenceIDGenerator:
    """Generate unique evidence identifiers scoped to a run.

    IDs follow the pattern `{prefix}-{date}-{sequence:04d}` where the date is derived
    from the active run identifier (e.g. `20251024` from `20251024_193012Z`).
    Sequence numbers are per-prefix and reset for each run.
    """

    run_id: str
    _counters: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must be provided for EvidenceIDGenerator")
        self._date_stamp = self.run_id.split("_", 1)[0]
        if not self._date_stamp.isdigit() or len(self._date_stamp) != 8:
            raise ValueError(f"run_id '{self.run_id}' must begin with YYYYMMDD")

    def next_id(self, prefix: str) -> str:
        """Return the next sequential ID for the given prefix."""
        if not prefix or not prefix.isalpha():
            raise ValueError("prefix must be a non-empty alphabetic string")

        counter = self._counters.get(prefix.upper(), 0) + 1
        self._counters[prefix.upper()] = counter
        return f"{prefix.upper()}-{self._date_stamp}-{counter:04d}"

    @property
    def counters(self) -> Dict[str, int]:
        """Expose counters for testing/inspection (copy)."""
        return dict(self._counters)
