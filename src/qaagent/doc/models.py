"""Pydantic models for app documentation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IntegrationType(str, Enum):
    """Type of external integration."""

    HTTP_CLIENT = "http_client"
    SDK = "sdk"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    STORAGE = "storage"
    AUTH_PROVIDER = "auth_provider"
    WEBHOOK = "webhook"
    UNKNOWN = "unknown"


class RouteDoc(BaseModel):
    """Documentation for a single route."""

    path: str
    method: str
    summary: Optional[str] = None
    description: Optional[str] = None
    auth_required: bool = False
    params: Dict[str, Any] = Field(default_factory=dict)
    responses: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class FeatureArea(BaseModel):
    """A logical grouping of related routes representing a feature."""

    id: str
    name: str
    description: str = ""
    routes: List[RouteDoc] = Field(default_factory=list)
    crud_operations: List[str] = Field(default_factory=list)  # e.g. ["create", "read", "update", "delete"]
    auth_required: bool = False
    integration_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    @property
    def route_count(self) -> int:
        return len(self.routes)

    @property
    def has_full_crud(self) -> bool:
        return all(op in self.crud_operations for op in ["create", "read", "update", "delete"])


class Integration(BaseModel):
    """An external service or dependency detected in the codebase."""

    id: str
    name: str
    type: IntegrationType = IntegrationType.UNKNOWN
    description: str = ""
    package: Optional[str] = None
    env_vars: List[str] = Field(default_factory=list)
    connected_features: List[str] = Field(default_factory=list)
    source: str = "auto"  # "auto" or "config"


class CujStep(BaseModel):
    """A single step in a discovered CUJ."""

    order: int
    action: str
    route: Optional[str] = None
    method: Optional[str] = None


class DiscoveredCUJ(BaseModel):
    """A critical user journey inferred from route analysis."""

    id: str
    name: str
    description: str = ""
    pattern: str = ""  # e.g. "auth_flow", "crud_lifecycle"
    steps: List[CujStep] = Field(default_factory=list)
    feature_ids: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class ArchitectureNode(BaseModel):
    """A node in the architecture diagram."""

    id: str
    label: str
    type: str  # "feature", "integration", "route_group"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, float]] = None  # {x, y} for layout


class ArchitectureEdge(BaseModel):
    """An edge in the architecture diagram."""

    id: str
    source: str
    target: str
    label: Optional[str] = None
    type: str = "default"  # "default", "shared_integration", "parent_child"


class AppDocumentation(BaseModel):
    """Complete documentation for an application."""

    app_name: str
    summary: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    content_hash: str = ""
    source_dir: Optional[str] = None
    features: List[FeatureArea] = Field(default_factory=list)
    integrations: List[Integration] = Field(default_factory=list)
    discovered_cujs: List[DiscoveredCUJ] = Field(default_factory=list)
    architecture_nodes: List[ArchitectureNode] = Field(default_factory=list)
    architecture_edges: List[ArchitectureEdge] = Field(default_factory=list)
    total_routes: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
