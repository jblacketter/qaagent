from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class RouteSource(str, Enum):
    """Represents where a discovered route originated from."""

    OPENAPI = "openapi"
    CODE = "code_analysis"
    RUNTIME = "runtime"
    MANUAL = "manual"


@dataclass
class Route:
    """Normalized representation of an API or UI route."""

    path: str
    method: str
    auth_required: bool
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    responses: Dict[str, Any] = field(default_factory=dict)
    source: RouteSource = RouteSource.OPENAPI
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["source"] = self.source.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Route":
        return cls(
            path=data["path"],
            method=data["method"],
            auth_required=data.get("auth_required", False),
            summary=data.get("summary"),
            description=data.get("description"),
            tags=list(data.get("tags", []) or []),
            params=dict(data.get("params", {}) or {}),
            responses=dict(data.get("responses", {}) or {}),
            source=RouteSource(data.get("source", RouteSource.OPENAPI.value)),
            confidence=float(data.get("confidence", 1.0)),
            metadata=dict(data.get("metadata", {}) or {}),
        )


class RiskCategory(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    QUALITY = "quality"


class RiskSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


SEVERITY_SCORES: Dict[RiskSeverity, int] = {
    RiskSeverity.CRITICAL: 5,
    RiskSeverity.HIGH: 4,
    RiskSeverity.MEDIUM: 3,
    RiskSeverity.LOW: 2,
    RiskSeverity.INFO: 1,
}


@dataclass
class Risk:
    """Represents a discovered risk with optional references."""

    category: RiskCategory
    severity: RiskSeverity
    route: Optional[str]
    title: str
    description: str
    recommendation: str
    source: str = "rule"
    cwe_id: Optional[str] = None
    owasp_top_10: Optional[str] = None
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def score(self) -> int:
        return SEVERITY_SCORES.get(self.severity, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "route": self.route,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "source": self.source,
            "cwe_id": self.cwe_id,
            "owasp_top_10": self.owasp_top_10,
            "references": list(self.references),
            "metadata": dict(self.metadata),
            "score": self.score(),
        }


@dataclass
class StrategySummary:
    """Aggregate view of the generated strategy for reporting."""

    total_routes: int
    critical_routes: int
    risks: List[Risk] = field(default_factory=list)
    recommended_tests: Dict[str, Any] = field(default_factory=dict)
    priorities: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_routes": self.total_routes,
            "critical_routes": self.critical_routes,
            "risks": [risk.to_dict() for risk in self.risks],
            "recommended_tests": self.recommended_tests,
            "priorities": self.priorities,
            "metadata": self.metadata,
        }
