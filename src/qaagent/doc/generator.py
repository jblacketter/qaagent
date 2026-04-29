"""Silent shim — qaagent.doc.generator re-exports from qa_docgen.

The DeprecationWarning is emitted once by the package __init__.py; sub-file
shims stay quiet to avoid spamming every direct-module import.

`discover_routes` is also re-exported here so legacy
`patch("qaagent.doc.generator.discover_routes", ...)` targets resolve at
decoration time.
"""
from qa_docgen.generator import *  # noqa: F401,F403
from qa_docgen.generator import (  # noqa: F401 — explicit for linters / patch targets
    APPDOC_FILENAME,
    _apply_doc_settings,
    _compute_content_hash,
    generate_documentation,
    load_documentation,
    save_documentation,
)
from qaagent.analyzers.route_discovery import discover_routes  # noqa: F401 — patch target
