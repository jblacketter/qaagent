"""Silent shim — qaagent.doc.cuj_discoverer re-exports from qa_docgen."""
from qa_docgen.cuj_discoverer import *  # noqa: F401,F403
from qa_docgen.cuj_discoverer import discover_cujs, to_cuj_config  # noqa: F401
