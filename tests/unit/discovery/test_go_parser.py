"""Tests for Go route parser."""
from pathlib import Path

from qaagent.discovery.go_parser import GoParser


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "discovery" / "go_project"


class TestGoParser:
    def setup_method(self):
        self.parser = GoParser()

    def test_find_route_files(self):
        files = self.parser.find_route_files(FIXTURES)
        assert len(files) == 1
        assert files[0].name == "main.go"

    def test_parse_sample_app(self):
        routes = self.parser.parse(FIXTURES)
        paths = {f"{route.method} {route.path}" for route in routes}

        assert "GET /health" in paths
        assert "GET /metrics" in paths
        assert "GET /api/items/{id}" in paths
        assert "POST /api/items" in paths
        assert "GET /api/files/{path}" in paths
        assert "PUT /v1/users/{id}" in paths
        assert "DELETE /v1/users/{id}" in paths

    def test_auth_detection_for_group_middleware(self):
        routes = self.parser.parse(FIXTURES)
        create_item = next((r for r in routes if r.path == "/api/items" and r.method == "POST"), None)
        assert create_item is not None
        assert create_item.auth_required is True

    def test_params_compatible_with_consumers(self):
        routes = self.parser.parse(FIXTURES)
        item_route = next((r for r in routes if r.path == "/api/items/{id}" and r.method == "GET"), None)
        assert item_route is not None
        assert item_route.params.get("query", []) == []
        assert item_route.params["path"][0]["name"] == "id"
