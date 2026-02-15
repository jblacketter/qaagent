"""Tests for Ruby route parser."""
from pathlib import Path

from qaagent.discovery.ruby_parser import RubyParser


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "discovery" / "ruby_project"


class TestRubyParser:
    def setup_method(self):
        self.parser = RubyParser()

    def test_find_route_files(self):
        files = self.parser.find_route_files(FIXTURES)
        names = {file.name for file in files}
        assert "routes.rb" in names
        assert "app.rb" in names

    def test_parse_rails_and_sinatra_routes(self):
        routes = self.parser.parse(FIXTURES)
        paths = {f"{route.method} {route.path}" for route in routes}

        assert "GET /api/users" in paths
        assert "POST /api/users" in paths
        assert "GET /api/users/{id}" in paths
        assert "PATCH /api/users/{id}" in paths
        assert "DELETE /api/users/{id}" in paths
        assert "GET /api/health" in paths
        assert "POST /api/status" in paths
        assert "GET /public" in paths
        assert "POST /login" in paths
        assert "PUT /users/{id}" in paths

    def test_auth_detection(self):
        routes = self.parser.parse(FIXTURES)
        login = next((r for r in routes if r.path == "/login" and r.method == "POST"), None)
        assert login is not None
        assert login.auth_required is True

    def test_params_compatible_with_consumers(self):
        routes = self.parser.parse(FIXTURES)
        user_route = next((r for r in routes if r.path == "/users/{id}" and r.method == "PUT"), None)
        assert user_route is not None
        assert user_route.params.get("query", []) == []
        assert user_route.params["path"][0]["name"] == "id"
