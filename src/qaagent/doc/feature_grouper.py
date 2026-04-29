"""Silent shim — qaagent.doc.feature_grouper re-exports from qa_docgen."""
from qa_docgen.feature_grouper import *  # noqa: F401,F403
from qa_docgen.feature_grouper import (  # noqa: F401 — private helpers needed by tests
    _extract_prefix,
    _slugify,
    group_routes,
)
