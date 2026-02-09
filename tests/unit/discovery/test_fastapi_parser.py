"""Tests for FastAPI route parser."""
from pathlib import Path

import pytest

from qaagent.discovery.fastapi_parser import FastAPIParser


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "discovery" / "fastapi_project"


class TestFastAPIParser:
    def setup_method(self):
        self.parser = FastAPIParser()

    def test_find_route_files(self, tmp_path):
        """Should find Python files with FastAPI decorators."""
        (tmp_path / "main.py").write_text('@app.get("/health")\ndef health(): pass')
        (tmp_path / "utils.py").write_text("def helper(): pass")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text('@app.get("/test")\ndef test(): pass')

        files = self.parser.find_route_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_parse_sample_app(self):
        """Should discover routes from sample FastAPI app."""
        routes = self.parser.parse(FIXTURES)
        # Filter to only fastapi routes
        fa_routes = [r for r in routes if r.metadata.get("source") == "fastapi"]

        assert len(fa_routes) > 0

        paths = {f"{r.method} {r.path}" for r in fa_routes}
        assert "GET /health" in paths
        assert "POST /login" in paths

    def test_parse_router_routes(self):
        """Should discover routes with APIRouter prefix."""
        routes = self.parser.parse(FIXTURES)
        fa_routes = [r for r in routes if r.metadata.get("source") == "fastapi"]

        paths = {f"{r.method} {r.path}" for r in fa_routes}
        assert "GET /api/v1/items" in paths
        assert "GET /api/v1/items/{item_id}" in paths
        assert "POST /api/v1/items" in paths
        assert "PUT /api/v1/items/{item_id}" in paths
        assert "DELETE /api/v1/items/{item_id}" in paths

    def test_path_params_normalized(self):
        """Route.params should use Dict[str, List[dict]] shape."""
        routes = self.parser.parse(FIXTURES)
        item_route = next(
            (r for r in routes if r.path == "/api/v1/items/{item_id}" and r.method == "GET"),
            None,
        )
        assert item_route is not None
        assert "path" in item_route.params
        path_params = item_route.params["path"]
        assert isinstance(path_params, list)
        assert len(path_params) >= 1
        assert path_params[0]["name"] == "item_id"
        assert path_params[0]["type"] == "integer"

    def test_auth_detection(self):
        """Routes with Depends(get_current_user) should have auth_required=True."""
        routes = self.parser.parse(FIXTURES)
        create_route = next(
            (r for r in routes if r.path == "/api/v1/items" and r.method == "POST"),
            None,
        )
        assert create_route is not None
        assert create_route.auth_required is True

    def test_no_auth_route(self):
        """Routes without auth deps should have auth_required=False."""
        routes = self.parser.parse(FIXTURES)
        health = next((r for r in routes if r.path == "/health"), None)
        assert health is not None
        assert health.auth_required is False

    def test_tags_extracted(self):
        """Tags from decorator should be preserved."""
        routes = self.parser.parse(FIXTURES)
        item_route = next(
            (r for r in routes if r.path == "/api/v1/items" and r.method == "GET"),
            None,
        )
        assert item_route is not None
        assert "items" in item_route.tags

    def test_source_is_code(self):
        """All routes should have source=CODE."""
        routes = self.parser.parse(FIXTURES)
        for route in routes:
            if route.metadata.get("source") == "fastapi":
                assert route.source.value == "code_analysis"

    def test_confidence(self):
        """Parser routes should have confidence < 1.0."""
        routes = self.parser.parse(FIXTURES)
        for route in routes:
            if route.metadata.get("source") == "fastapi":
                assert route.confidence == 0.9

    def test_empty_directory(self, tmp_path):
        """Should return empty list for directory with no Python files."""
        routes = self.parser.parse(tmp_path)
        assert routes == []

    def test_syntax_error_file(self, tmp_path):
        """Should skip files with syntax errors."""
        (tmp_path / "bad.py").write_text("def broken(:\n  pass")
        routes = self.parser.parse(tmp_path)
        assert routes == []

    def test_params_compatible_with_consumers(self):
        """Params should work with route.params.get('query', []) and route.params['path']."""
        routes = self.parser.parse(FIXTURES)

        # Test a route with path params
        item_route = next(
            (r for r in routes if r.path == "/api/v1/items/{item_id}" and r.method == "GET"),
            None,
        )
        assert item_route is not None

        # Consumer pattern from risk_assessment.py
        query_params = item_route.params.get("query", [])
        assert isinstance(query_params, list)

        # Consumer pattern from openapi_gen
        path_params = item_route.params["path"]
        assert isinstance(path_params, list)
        for p in path_params:
            # Should work with both dict access patterns
            name = p if isinstance(p, str) else p.get("name")
            assert name is not None
