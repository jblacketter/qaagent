"""Tests for Rust route parser."""
from pathlib import Path

from qaagent.discovery.rust_parser import RustParser


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "discovery" / "rust_project"


class TestRustParser:
    def setup_method(self):
        self.parser = RustParser()

    def test_find_route_files(self):
        files = self.parser.find_route_files(FIXTURES)
        assert len(files) == 1
        assert files[0].name == "main.rs"

    def test_parse_actix_and_axum_routes(self):
        routes = self.parser.parse(FIXTURES)
        paths = {f"{route.method} {route.path}" for route in routes}

        assert "GET /health" in paths
        assert "POST /login" in paths
        assert "GET /items/{id}" in paths
        assert "POST /items" in paths
        assert "GET /users/{id}" in paths
        assert "POST /users" in paths
        assert "GET /admin" in paths
        assert "POST /admin" in paths

    def test_auth_detection(self):
        routes = self.parser.parse(FIXTURES)
        admin = next((r for r in routes if r.path == "/admin" and r.method == "POST"), None)
        assert admin is not None
        assert admin.auth_required is True

    def test_params_compatible_with_consumers(self):
        routes = self.parser.parse(FIXTURES)
        user_route = next((r for r in routes if r.path == "/users/{id}" and r.method == "GET"), None)
        assert user_route is not None
        assert user_route.params.get("query", []) == []
        assert user_route.params["path"][0]["name"] == "id"
