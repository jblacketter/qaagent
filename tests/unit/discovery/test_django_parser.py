"""Tests for Django route parser."""
from pathlib import Path

import pytest

from qaagent.discovery.django_parser import DjangoParser


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "discovery" / "django_project"


class TestDjangoParser:
    def setup_method(self):
        self.parser = DjangoParser()

    def test_find_route_files(self, tmp_path):
        """Should find urls.py and views.py files."""
        (tmp_path / "urls.py").write_text("urlpatterns = []")
        (tmp_path / "views.py").write_text("def index(): pass")
        (tmp_path / "utils.py").write_text("def helper(): pass")

        files = self.parser.find_route_files(tmp_path)
        names = {f.name for f in files}
        assert "urls.py" in names
        assert "views.py" in names
        assert "utils.py" not in names

    def test_parse_url_patterns(self):
        """Should extract path() patterns from urls.py."""
        routes = self.parser.parse(FIXTURES)
        django_routes = [r for r in routes if r.metadata.get("source") == "django"]

        assert len(django_routes) > 0
        paths = {r.path for r in django_routes}
        # URL patterns from django_urls.py
        assert any("/users" in p for p in paths)
        assert any("/items" in p for p in paths)

    def test_path_params_normalized(self):
        """Django <int:pk> should normalize to {pk}."""
        routes = self.parser.parse(FIXTURES)
        django_routes = [r for r in routes if r.metadata.get("source") == "django"]

        pk_route = next((r for r in django_routes if "{pk}" in r.path), None)
        assert pk_route is not None
        assert "<" not in pk_route.path
        assert "path" in pk_route.params
        params = pk_route.params["path"]
        assert any(p["name"] == "pk" and p["type"] == "integer" for p in params)

    def test_slug_converter(self):
        """Django <slug:slug> should produce type=string."""
        routes = self.parser.parse(FIXTURES)
        django_routes = [r for r in routes if r.metadata.get("source") == "django"]

        slug_route = next((r for r in django_routes if "{slug}" in r.path), None)
        assert slug_route is not None
        params = slug_route.params["path"]
        assert any(p["name"] == "slug" for p in params)

    def test_drf_viewset_routes(self):
        """Should discover DRF ViewSet CRUD routes."""
        routes = self.parser.parse(FIXTURES)
        drf_routes = [r for r in routes if r.metadata.get("source") == "django-drf"]

        assert len(drf_routes) > 0

        # ItemViewSet is ModelViewSet: should have all CRUD actions
        item_routes = [r for r in drf_routes if r.metadata.get("viewset") == "ItemViewSet"]
        item_methods = {r.method for r in item_routes}
        assert "GET" in item_methods
        assert "POST" in item_methods
        assert "PUT" in item_methods
        assert "DELETE" in item_methods

    def test_drf_custom_action(self):
        """Should discover @action decorated methods."""
        routes = self.parser.parse(FIXTURES)
        drf_routes = [r for r in routes if r.metadata.get("source") == "django-drf"]

        archive_route = next(
            (r for r in drf_routes if r.metadata.get("action") == "archive"),
            None,
        )
        assert archive_route is not None
        assert archive_route.method == "POST"
        assert "{pk}" in archive_route.path

        recent_route = next(
            (r for r in drf_routes if r.metadata.get("action") == "recent"),
            None,
        )
        assert recent_route is not None
        assert recent_route.method == "GET"

    def test_drf_readonly_viewset(self):
        """ReadOnlyModelViewSet should only have list + retrieve."""
        routes = self.parser.parse(FIXTURES)
        drf_routes = [r for r in routes if r.metadata.get("source") == "django-drf"]
        user_routes = [r for r in drf_routes if r.metadata.get("viewset") == "UserViewSet"]

        methods = {r.method for r in user_routes}
        assert methods == {"GET"}  # list and retrieve are both GET

    def test_viewset_auth(self):
        """ViewSet with permission_classes=[IsAuthenticated] should be auth_required."""
        routes = self.parser.parse(FIXTURES)
        item_drf = [
            r for r in routes if r.metadata.get("viewset") == "ItemViewSet"
        ]
        assert all(r.auth_required for r in item_drf)

    def test_source_is_code(self):
        routes = self.parser.parse(FIXTURES)
        for route in routes:
            if "django" in route.metadata.get("source", ""):
                assert route.source.value == "code_analysis"

    def test_empty_directory(self, tmp_path):
        routes = self.parser.parse(tmp_path)
        assert routes == []

    def test_params_compatible_with_consumers(self):
        """Params should work with existing consumer patterns."""
        routes = self.parser.parse(FIXTURES)
        pk_route = next(
            (r for r in routes if "{pk}" in r.path and "path" in r.params),
            None,
        )
        assert pk_route is not None

        # risk_assessment pattern
        query = pk_route.params.get("query", [])
        assert isinstance(query, list)

        # openapi_gen pattern
        path_params = pk_route.params["path"]
        for p in path_params:
            name = p if isinstance(p, str) else p.get("name")
            assert name is not None
