"""Tests for Flask route parser."""
from pathlib import Path

import pytest

from qaagent.discovery.flask_parser import FlaskParser


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "discovery" / "flask_project"


class TestFlaskParser:
    def setup_method(self):
        self.parser = FlaskParser()

    def test_find_route_files(self, tmp_path):
        """Should find Python files with Flask route decorators."""
        (tmp_path / "app.py").write_text('@app.route("/health")\ndef health(): pass')
        (tmp_path / "utils.py").write_text("def helper(): pass")

        files = self.parser.find_route_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "app.py"

    def test_parse_sample_app(self):
        """Should discover routes from sample Flask app."""
        routes = self.parser.parse(FIXTURES)
        flask_routes = [r for r in routes if r.metadata.get("source") == "flask"]

        assert len(flask_routes) > 0

        paths = {f"{r.method} {r.path}" for r in flask_routes}
        assert "GET /health" in paths
        assert "POST /login" in paths

    def test_blueprint_prefix(self):
        """Should compose Blueprint url_prefix with route path."""
        routes = self.parser.parse(FIXTURES)
        flask_routes = [r for r in routes if r.metadata.get("source") == "flask"]

        paths = {f"{r.method} {r.path}" for r in flask_routes}
        assert "GET /api/v1/items" in paths
        assert "POST /api/v1/items" in paths

    def test_path_params_normalized(self):
        """Flask <int:item_id> should be normalized to {item_id}."""
        routes = self.parser.parse(FIXTURES)
        item_route = next(
            (r for r in routes if "{item_id}" in r.path and r.method == "GET" and r.metadata.get("source") == "flask"),
            None,
        )
        assert item_route is not None
        assert "<" not in item_route.path
        assert "{item_id}" in item_route.path
        assert "path" in item_route.params
        params = item_route.params["path"]
        assert any(p["name"] == "item_id" and p["type"] == "integer" for p in params)

    def test_uuid_converter(self):
        """Flask <uuid:user_id> should produce type=uuid."""
        routes = self.parser.parse(FIXTURES)
        user_route = next(
            (r for r in routes if "{user_id}" in r.path and r.metadata.get("source") == "flask"),
            None,
        )
        assert user_route is not None
        params = user_route.params["path"]
        assert any(p["name"] == "user_id" and p["type"] == "uuid" for p in params)

    def test_multiple_methods(self):
        """@app.route with methods=["PUT", "PATCH"] should create separate routes."""
        routes = self.parser.parse(FIXTURES)
        flask_routes = [r for r in routes if r.metadata.get("source") == "flask"]
        update_routes = [r for r in flask_routes if "update_item" in r.metadata.get("function", "")]
        methods = {r.method for r in update_routes}
        assert "PUT" in methods
        assert "PATCH" in methods

    def test_auth_detection(self):
        """Routes with @login_required should have auth_required=True."""
        routes = self.parser.parse(FIXTURES)
        create_route = next(
            (r for r in routes if r.metadata.get("function") == "create_item" and r.metadata.get("source") == "flask"),
            None,
        )
        assert create_route is not None
        assert create_route.auth_required is True

    def test_no_auth_route(self):
        routes = self.parser.parse(FIXTURES)
        health = next(
            (r for r in routes if r.path == "/health" and r.metadata.get("source") == "flask"),
            None,
        )
        assert health is not None
        assert health.auth_required is False

    def test_source_is_code(self):
        routes = self.parser.parse(FIXTURES)
        for route in routes:
            if route.metadata.get("source") == "flask":
                assert route.source.value == "code_analysis"

    def test_empty_directory(self, tmp_path):
        routes = self.parser.parse(tmp_path)
        assert routes == []

    def test_params_compatible_with_consumers(self):
        """Params should work with existing consumer patterns."""
        routes = self.parser.parse(FIXTURES)
        item_route = next(
            (r for r in routes if "{item_id}" in r.path and r.method == "GET" and r.metadata.get("source") == "flask"),
            None,
        )
        assert item_route is not None

        # route.params.get("query", []) — risk_assessment pattern
        query = item_route.params.get("query", [])
        assert isinstance(query, list)

        # route.params["path"] — openapi_gen pattern
        path_params = item_route.params["path"]
        for p in path_params:
            name = p if isinstance(p, str) else p.get("name")
            assert name is not None
