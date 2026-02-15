from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from qaagent.analyzers.models import RouteSource
from qaagent.analyzers.route_discovery import (
    deduplicate_routes,
    discover_from_openapi,
    discover_from_source,
    discover_routes,
)
from qaagent.analyzers.ui_crawler import CrawlPage


FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "routes"
DISCOVERY_FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "discovery"


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
    duplicate = original[0].model_copy(deep=True)
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


def test_discover_from_source_go_parser() -> None:
    routes = discover_from_source(DISCOVERY_FIXTURES / "go_project", framework="go")
    assert any(route.path == "/api/items/{id}" and route.method == "GET" for route in routes)
    assert any(route.path == "/v1/users/{id}" and route.method == "PUT" for route in routes)


def test_discover_from_source_ruby_parser() -> None:
    routes = discover_from_source(DISCOVERY_FIXTURES / "ruby_project", framework="ruby")
    assert any(route.path == "/api/users" and route.method == "GET" for route in routes)
    assert any(route.path == "/users/{id}" and route.method == "PUT" for route in routes)


def test_discover_from_source_rust_parser() -> None:
    routes = discover_from_source(DISCOVERY_FIXTURES / "rust_project", framework="rust")
    assert any(route.path == "/health" and route.method == "GET" for route in routes)
    assert any(route.path == "/users/{id}" and route.method == "GET" for route in routes)


def test_discover_from_source_auto_detect_go() -> None:
    routes = discover_from_source(DISCOVERY_FIXTURES / "go_project")
    assert any(route.path == "/health" and route.method == "GET" for route in routes)


def test_discover_from_source_auto_detect_ruby() -> None:
    routes = discover_from_source(DISCOVERY_FIXTURES / "ruby_project")
    assert any(route.path == "/api/users" and route.method == "GET" for route in routes)


def test_discover_from_source_auto_detect_rust() -> None:
    routes = discover_from_source(DISCOVERY_FIXTURES / "rust_project")
    assert any(route.path == "/users/{id}" and route.method == "GET" for route in routes)


def test_discover_routes_with_runtime_crawl() -> None:
    fake_pages = [
        CrawlPage(url="https://app.example.com", path="/", title="Home", depth=0, internal=True),
        CrawlPage(url="https://app.example.com/account", path="/account", title="Account", depth=1, internal=True),
    ]

    with patch("qaagent.analyzers.route_discovery.crawl_ui_routes", return_value=fake_pages):
        routes = discover_routes(
            crawl=True,
            crawl_url="https://app.example.com",
            crawl_depth=2,
            crawl_max_pages=10,
        )

    assert len(routes) == 2
    assert all(route.source == RouteSource.RUNTIME for route in routes)
    assert all(route.method == "GET" for route in routes)
    assert routes[0].metadata["crawl_url"] == "https://app.example.com"
    assert routes[1].metadata["crawl_depth"] == 1


def test_discover_routes_merges_openapi_and_runtime_duplicates() -> None:
    spec_path = FIXTURE_DIR / "secure_openapi.yaml"
    fake_pages = [
        CrawlPage(url="https://app.example.com/items", path="/items", title="Items", depth=0, internal=True),
    ]

    with patch("qaagent.analyzers.route_discovery.crawl_ui_routes", return_value=fake_pages):
        routes = discover_routes(
            openapi_path=spec_path,
            crawl=True,
            crawl_url="https://app.example.com",
        )

    # OpenAPI has GET /items and POST /items. Runtime crawl adds only GET /items.
    assert len(routes) == 2
    get_route = next(route for route in routes if route.method == "GET")
    assert get_route.source == RouteSource.OPENAPI
    assert get_route.confidence == 1.0
