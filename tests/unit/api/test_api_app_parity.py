"""Verify that api/app.py mounts all the same API routers as web_ui.py.

The web_ui.py app has additional inline routes (/api/targets, /api/commands/*, etc.)
that are web-UI-specific. This test only checks that every router module imported by
web_ui.py is also imported and mounted in api/app.py.
"""

from __future__ import annotations


def _router_prefixed_paths(app) -> set[str]:
    """Extract route paths contributed by include_router (have tags from routers)."""
    paths: set[str] = set()
    for route in app.routes:
        # Routes added via include_router have tags from their router
        if hasattr(route, "path") and route.path.startswith("/api"):
            if hasattr(route, "tags") and route.tags:
                paths.add(route.path)
    return paths


def test_standalone_api_mounts_all_router_routes():
    """Every router-contributed /api/* route in web_ui.py must also exist in api/app.py."""
    from qaagent.api.app import create_app as create_api_app
    from qaagent.web_ui import app as web_ui_app

    api_paths = _router_prefixed_paths(create_api_app())
    web_paths = _router_prefixed_paths(web_ui_app)

    missing = web_paths - api_paths
    assert not missing, f"Router routes in web_ui.py but not in api/app.py: {sorted(missing)}"


def test_api_app_has_agent_routes():
    """The standalone API app must have agent endpoints."""
    from qaagent.api.app import create_app
    app = create_app()
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/agent/config" in paths
    assert "/api/agent/analyze" in paths
    assert "/api/agent/usage" in paths


def test_api_app_has_auth_routes():
    """The standalone API app must have auth endpoints."""
    from qaagent.api.app import create_app
    app = create_app()
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/auth/status" in paths
    assert "/api/auth/login" in paths
    assert "/api/auth/setup" in paths
    assert "/api/auth/logout" in paths
    assert "/api/auth/change-password" in paths


def test_api_app_has_settings_routes():
    """The standalone API app must have settings endpoints."""
    from qaagent.api.app import create_app
    app = create_app()
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/settings" in paths
    assert "/api/settings/clear-database" in paths
