"""Silent shim — qaagent.doc.graph_builder re-exports from qa_docgen."""
from qa_docgen.graph_builder import *  # noqa: F401,F403
from qa_docgen.graph_builder import (  # noqa: F401 — explicit for linters / tests
    _path_matches_prefix,
    build_all_graphs,
    build_feature_map,
    build_integration_map,
    build_route_graph,
)
