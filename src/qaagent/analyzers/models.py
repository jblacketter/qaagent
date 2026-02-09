"""Data models for route discovery, risk assessment, and strategy generation.

These models use Pydantic BaseModel for validation, serialization, and JSON schema generation.
Backward-compatible to_dict() and from_dict() methods are provided for existing callers.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


class RouteSource(str, Enum):
    """Represents where a discovered route originated from."""

    OPENAPI = "openapi"
    CODE = "code_analysis"
    RUNTIME = "runtime"
    MANUAL = "manual"


class Route(BaseModel):
    """Normalized representation of an API or UI route."""

    path: str
    method: str
    auth_required: bool
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)
    responses: Dict[str, Any] = Field(default_factory=dict)
    source: RouteSource = RouteSource.OPENAPI
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict with enum values as strings (backward compat)."""
        data = self.model_dump()
        data["source"] = self.source.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Route:
        """Deserialize from dict (backward compat)."""
        return cls.model_validate(data)


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


class Risk(BaseModel):
    """Represents a discovered risk with optional references."""

    category: RiskCategory
    severity: RiskSeverity
    route: Optional[str] = None
    title: str
    description: str
    recommendation: str
    source: str = "rule"
    cwe_id: Optional[str] = None
    owasp_top_10: Optional[str] = None
    references: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def score(self) -> int:
        """Numeric score derived from severity."""
        return SEVERITY_SCORES.get(self.severity, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict with enum values as strings (backward compat)."""
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
            "score": self.score,
        }


class StrategySummary(BaseModel):
    """Aggregate view of the generated strategy for reporting."""

    total_routes: int
    critical_routes: int
    risks: List[Risk] = Field(default_factory=list)
    recommended_tests: Dict[str, Any] = Field(default_factory=dict)
    priorities: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (backward compat)."""
        return {
            "total_routes": self.total_routes,
            "critical_routes": self.critical_routes,
            "risks": [risk.to_dict() for risk in self.risks],
            "recommended_tests": self.recommended_tests,
            "priorities": self.priorities,
            "metadata": self.metadata,
        }
