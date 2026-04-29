"""Silent shim — qaagent.doc.models re-exports from qa_docgen.

The DeprecationWarning is emitted once by the package __init__.py; sub-file
shims stay quiet to avoid spamming every direct-module import.
"""
from qa_docgen.models import *  # noqa: F401,F403
from qa_docgen.models import (  # noqa: F401 — explicit for linters / patch targets
    AgentAnalysis,
    AppDocumentation,
    ArchitectureEdge,
    ArchitectureNode,
    CujStep,
    DiscoveredCUJ,
    DocSection,
    FeatureArea,
    Integration,
    IntegrationType,
    JourneyStep,
    RouteDoc,
    UserJourney,
    UserRole,
)
