"""App documentation engine.

Generates living application specs from code analysis, route discovery,
and integration detection.
"""

from .generator import generate_documentation, save_documentation, load_documentation
from .models import (
    AppDocumentation,
    ArchitectureEdge,
    ArchitectureNode,
    DiscoveredCUJ,
    FeatureArea,
    Integration,
    IntegrationType,
    RouteDoc,
)

__all__ = [
    "generate_documentation",
    "save_documentation",
    "load_documentation",
    "AppDocumentation",
    "ArchitectureEdge",
    "ArchitectureNode",
    "DiscoveredCUJ",
    "FeatureArea",
    "Integration",
    "IntegrationType",
    "RouteDoc",
]
