"""Dataclasses describing evidence store records and manifest metadata."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ISO8601 = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> str:
    """Return current UTC timestamp in ISO8601 format."""
    return datetime.now(timezone.utc).strftime(ISO8601)


@dataclass
class TargetMetadata:
    """Metadata describing the analyzed target repository."""

    name: str
    path: str
    git: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolStatus:
    """Execution status for a single tool/collector."""

    version: Optional[str] = None
    executed: bool = False
    exit_code: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Manifest:
    """Top-level manifest for a run."""

    run_id: str
    created_at: str
    target: TargetMetadata
    tools: Dict[str, ToolStatus] = field(default_factory=dict)
    counts: Dict[str, int] = field(
        default_factory=lambda: {
            "findings": 0,
            "risks": 0,
            "tests": 0,
            "coverage_components": 0,
        }
    )
    evidence_files: Dict[str, str] = field(default_factory=dict)
    diagnostics: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        defaults = {
            "findings": 0,
            "risks": 0,
            "tests": 0,
            "coverage_components": 0,
        }
        for key, value in defaults.items():
            self.counts.setdefault(key, value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "target": self.target.to_dict(),
            "tools": {key: status.to_dict() for key, status in self.tools.items()},
            "counts": dict(self.counts),
            "evidence_files": dict(self.evidence_files),
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manifest":
        target_data = data.get("target", {}) or {}
        target = TargetMetadata(
            name=target_data.get("name", ""),
            path=target_data.get("path", ""),
            git=target_data.get("git", {}),
        )
        tools_data = {
            key: ToolStatus(
                version=tool_info.get("version"),
                executed=tool_info.get("executed", False),
                exit_code=tool_info.get("exit_code"),
                error=tool_info.get("error"),
            )
            for key, tool_info in (data.get("tools") or {}).items()
        }
        manifest = cls(
            run_id=data.get("run_id", ""),
            created_at=data.get("created_at", ""),
            target=target,
            tools=tools_data,
            counts=dict(data.get("counts", {})),
            evidence_files=dict(data.get("evidence_files", {})),
            diagnostics=list(data.get("diagnostics", [])),
        )
        return manifest

    def register_tool(self, name: str, status: ToolStatus) -> None:
        self.tools[name] = status

    def increment_count(self, key: str, amount: int) -> None:
        self.counts[key] = self.counts.get(key, 0) + amount

    def register_file(self, record_type: str, relative_path: str) -> None:
        self.evidence_files[record_type] = relative_path

    def add_diagnostic(self, message: str) -> None:
        self.diagnostics.append(message)


@dataclass
class FindingRecord:
    """Normalized lint/security/dependency finding."""

    evidence_id: str
    tool: str
    severity: str
    code: Optional[str]
    message: str
    file: Optional[str]
    line: Optional[int]
    column: Optional[int]
    tags: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    collected_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass
class CoverageRecord:
    """Coverage metric for a component or CUJ."""

    coverage_id: str
    type: str
    component: str
    value: float
    total_statements: Optional[int] = None
    covered_statements: Optional[int] = None
    sources: List[str] = field(default_factory=list)
    linked_cujs: List[str] = field(default_factory=list)
    collected_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChurnRecord:
    """Git churn statistics for a file."""

    evidence_id: str
    path: str
    window: str
    commits: int
    lines_added: int
    lines_deleted: int
    contributors: int
    last_commit_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApiRecord:
    """API surface metadata used in later sprints."""

    api_id: str
    method: str
    path: str
    auth_required: bool
    tags: List[str] = field(default_factory=list)
    source: str = "unknown"
    confidence: Optional[float] = None
    evidence_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestRecord:
    """Inventory entry for a test case (existing or generated)."""

    test_id: str
    kind: str
    name: str
    status: str
    last_run: Optional[str] = None
    evidence_refs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskRecord:
    """Computed risk score for a component or CUJ."""

    risk_id: str
    component: str
    score: float
    band: str
    confidence: float
    severity: str
    title: str
    description: str
    evidence_refs: List[str] = field(default_factory=list)
    factors: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0 and 100")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskRecord":
        return cls(
            risk_id=data.get("risk_id", ""),
            component=data.get("component", ""),
            score=float(data.get("score", 0.0)),
            band=data.get("band", "P3"),
            confidence=float(data.get("confidence", 0.0)),
            severity=data.get("severity", "low"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            evidence_refs=list(data.get("evidence_refs", [])),
            factors=dict(data.get("factors", {})),
            recommendations=list(data.get("recommendations", [])),
            created_at=data.get("created_at", utc_now()),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class RecommendationRecord:
    """Recommended actions derived from risk and coverage analysis."""

    recommendation_id: str
    component: str
    priority: str
    summary: str
    details: str
    evidence_refs: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecommendationRecord":
        return cls(
            recommendation_id=data.get("recommendation_id", ""),
            component=data.get("component", ""),
            priority=data.get("priority", "medium"),
            summary=data.get("summary", ""),
            details=data.get("details", ""),
            evidence_refs=list(data.get("evidence_refs", [])),
            created_at=data.get("created_at", utc_now()),
            metadata=dict(data.get("metadata", {})),
        )
