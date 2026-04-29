"""qaagent.doc — compatibility shim.

The application-documentation generator was extracted to the sibling
package `qa_docgen` on 2026-04-29 (Phase 6). This module re-exports the
public surface so legacy imports (`from qaagent.doc import ...`,
`from qaagent.doc.<submodule> import ...`) keep working. New code should
import from `qa_docgen` directly.
"""

import warnings

warnings.warn(
    "qaagent.doc has moved to qa_docgen — import from qa_docgen instead. "
    "This shim will be removed in a later cleanup phase.",
    DeprecationWarning,
    stacklevel=2,
)

from qa_docgen.generator import (  # noqa: E402, F401
    generate_documentation,
    save_documentation,
    load_documentation,
)
from qa_docgen.models import (  # noqa: E402, F401
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
