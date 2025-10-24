from __future__ import annotations

from pathlib import Path

from qaagent.analyzers.models import RouteSource
from qaagent.analyzers.route_discovery import (
    deduplicate_routes,
    discover_from_openapi,
    discover_routes,
)


FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "routes"


def test_discover_from_openapi_extracts_auth_and_metadata() -> None:
    spec_path = FIXTURE_DIR / "secure_openapi.yaml"
    routes = discover_from_openapi(spec_path)

    assert len(routes) == 2
    get_route = next(route for route in routes if route.method == "GET")
    post_route = next(route for route in routes if route.method == "POST")

    assert get_route.auth_required is True
    assert post_route.auth_required is False  # POST inherits global security which is empty
    assert get_route.metadata["security"]
    assert get_route.source == RouteSource.OPENAPI


def test_deduplicate_routes_prefers_higher_confidence() -> None:
    original = discover_from_openapi(FIXTURE_DIR / "secure_openapi.yaml")
    duplicate = original[0]
    duplicate.confidence = 0.5
    duplicate.metadata["source"] = "duplicate"

    merged = deduplicate_routes(original + [duplicate])
    assert len(merged) == 2
    route = merged[0]
    assert route.confidence == 1.0
    assert route.metadata.get("source") != "duplicate"


def test_discover_routes_with_openapi_only(tmp_path: Path) -> None:
    spec_path = FIXTURE_DIR / "secure_openapi.yaml"
    routes = discover_routes(openapi_path=spec_path)

    assert len(routes) == 2
    assert routes[0].path == "/items"
