"""Unit tests for UnitTestGenerator."""

from __future__ import annotations

from pathlib import Path

import pytest

from qaagent.analyzers.models import Route
from qaagent.generators.unit_test_generator import UnitTestGenerator


def sample_route(
    path: str = "/pets",
    method: str = "GET",
    auth_required: bool = False,
    tags: list[str] | None = None,
) -> Route:
    """Create a sample route for testing."""
    return Route(
        path=path,
        method=method,
        auth_required=auth_required,
        summary=f"{method} {path}",
        tags=tags or ["pets"],
        params={},
        responses={"200": {"description": "OK"}},
    )


class TestUnitTestGenerator:
    """Test suite for UnitTestGenerator."""

    def test_init(self) -> None:
        """Test generator initialization."""
        routes = [sample_route()]
        generator = UnitTestGenerator(routes=routes, base_url="http://localhost:8000")
        assert generator.routes == routes
        assert generator.base_url == "http://localhost:8000"
        assert generator.jinja_env is not None

    def test_group_routes_by_resource(self) -> None:
        """Test route grouping by resource name."""
        routes = [
            sample_route(path="/pets", method="GET"),
            sample_route(path="/pets", method="POST"),
            sample_route(path="/pets/{pet_id}", method="GET"),
            sample_route(path="/owners", method="GET"),
            sample_route(path="/health", method="GET", tags=["health"]),
        ]
        generator = UnitTestGenerator(routes=routes)
        resources = generator._group_routes_by_resource()

        assert "pets" in resources
        assert len(resources["pets"]) == 3  # GET, POST, GET with ID

        assert "owners" in resources
        assert len(resources["owners"]) == 1

        assert "health" in resources
        assert len(resources["health"]) == 1

    def test_group_routes_by_resource_root_path(self) -> None:
        """Test grouping routes with root path."""
        routes = [sample_route(path="/", method="GET")]
        generator = UnitTestGenerator(routes=routes)
        resources = generator._group_routes_by_resource()

        assert "root" in resources
        assert len(resources["root"]) == 1

    def test_sanitize_path(self) -> None:
        """Test path sanitization for Python identifiers."""
        generator = UnitTestGenerator(routes=[])

        assert generator._sanitize_path("/pets") == "pets"
        assert generator._sanitize_path("/pets/{pet_id}") == "pets_pet_id"
        assert generator._sanitize_path("/api/v1/pets/{id}") == "api_v1_pets_id"
        assert generator._sanitize_path("/") == ""

    def test_get_expected_status(self) -> None:
        """Test expected status code mapping."""
        generator = UnitTestGenerator(routes=[])

        assert generator._get_expected_status("GET") == 200
        assert generator._get_expected_status("POST") == 201
        assert generator._get_expected_status("PUT") == 200
        assert generator._get_expected_status("PATCH") == 200
        assert generator._get_expected_status("DELETE") == 204
        assert generator._get_expected_status("UNKNOWN") == 200  # fallback

    def test_generate_invalid_params(self) -> None:
        """Test invalid parameter generation."""
        route = sample_route(path="/pets/{pet_id}", method="GET")
        generator = UnitTestGenerator(routes=[route])

        params = generator._generate_invalid_params(route)

        assert -1 in params
        assert 0 in params
        assert "invalid" in params
        assert None in params
        assert "" in params

    def test_create_test_cases_get_request(self) -> None:
        """Test case creation for GET requests."""
        route = sample_route(path="/pets", method="GET")
        generator = UnitTestGenerator(routes=[route])

        cases = generator._create_test_cases(route)

        # GET requests should have at least a happy path test
        assert len(cases) >= 1
        assert cases[0]["type"] == "happy_path"
        assert cases[0]["expected_status"] == 200

    def test_create_test_cases_post_request(self) -> None:
        """Test case creation for POST requests."""
        route = sample_route(path="/pets", method="POST")
        generator = UnitTestGenerator(routes=[route])

        cases = generator._create_test_cases(route)

        # POST should have happy path + invalid data test
        assert len(cases) >= 2

        happy_path = [c for c in cases if c["type"] == "happy_path"]
        assert len(happy_path) == 1
        assert happy_path[0]["expected_status"] == 201

        invalid_data = [c for c in cases if c["type"] == "invalid_data"]
        assert len(invalid_data) == 1
        assert invalid_data[0]["expected_status"] == 422

    def test_create_test_cases_with_path_params(self) -> None:
        """Test case creation for routes with path parameters."""
        route = sample_route(path="/pets/{pet_id}", method="GET")
        generator = UnitTestGenerator(routes=[route])

        cases = generator._create_test_cases(route)

        # Should have parametrized test for invalid params
        parametrized = [c for c in cases if c["type"] == "parametrized"]
        assert len(parametrized) == 1
        assert "parameters" in parametrized[0]
        assert len(parametrized[0]["parameters"]) > 0

    def test_create_test_cases_put_request(self) -> None:
        """Test case creation for PUT requests."""
        route = sample_route(path="/pets/{pet_id}", method="PUT")
        generator = UnitTestGenerator(routes=[route])

        cases = generator._create_test_cases(route)

        # PUT should have happy path, invalid data, and parametrized tests
        assert len(cases) >= 3

        types = [c["type"] for c in cases]
        assert "happy_path" in types
        assert "invalid_data" in types
        assert "parametrized" in types

    def test_generate_creates_files(self, tmp_path: Path) -> None:
        """Test that generate() creates all expected files."""
        routes = [
            sample_route(path="/pets", method="GET"),
            sample_route(path="/pets", method="POST"),
            sample_route(path="/health", method="GET", tags=["health"]),
        ]
        generator = UnitTestGenerator(routes=routes)

        result = generator.generate(output_dir=tmp_path)

        # Check that files were created
        assert "test_pets" in result
        assert "test_health" in result
        assert "conftest" in result
        assert "init" in result

        # Verify files exist
        assert result["test_pets"].exists()
        assert result["test_health"].exists()
        assert result["conftest"].exists()
        assert result["init"].exists()

    def test_generate_test_file_content(self, tmp_path: Path) -> None:
        """Test that generated test files have valid Python content."""
        routes = [sample_route(path="/pets", method="GET")]
        generator = UnitTestGenerator(routes=routes)

        result = generator.generate(output_dir=tmp_path)
        test_file = result["test_pets"]

        content = test_file.read_text()

        # Check for pytest structure
        assert "import pytest" in content or "from pytest" in content or "def test_" in content
        assert "def test_" in content
        assert "class Test" in content

    def test_generate_conftest_content(self, tmp_path: Path) -> None:
        """Test that generated conftest.py has fixtures."""
        routes = [sample_route(path="/pets", method="GET")]
        generator = UnitTestGenerator(routes=routes)

        result = generator.generate(output_dir=tmp_path)
        conftest = result["conftest"]

        content = conftest.read_text()

        # Check for pytest fixtures
        assert "@pytest.fixture" in content or "pytest.fixture" in content

    def test_generate_creates_output_dir(self, tmp_path: Path) -> None:
        """Test that generate() creates output directory if it doesn't exist."""
        output_dir = tmp_path / "nested" / "test" / "dir"
        assert not output_dir.exists()

        routes = [sample_route()]
        generator = UnitTestGenerator(routes=routes)

        generator.generate(output_dir=output_dir)

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_generate_multiple_resources(self, tmp_path: Path) -> None:
        """Test generating tests for multiple resources."""
        routes = [
            sample_route(path="/pets", method="GET"),
            sample_route(path="/pets/{pet_id}", method="GET"),
            sample_route(path="/owners", method="GET"),
            sample_route(path="/owners/{owner_id}", method="PUT"),
            sample_route(path="/health", method="GET"),
        ]
        generator = UnitTestGenerator(routes=routes)

        result = generator.generate(output_dir=tmp_path)

        # Should create test files for each resource
        assert "test_pets" in result
        assert "test_owners" in result
        assert "test_health" in result

        # All files should exist
        for key, path in result.items():
            assert path.exists(), f"{key} file should exist"

    def test_generate_test_data_basic(self) -> None:
        """Test basic test data generation."""
        route = sample_route(path="/pets", method="POST")
        generator = UnitTestGenerator(routes=[route])

        data = generator._generate_test_data(route)

        # Should return empty dict or basic data
        assert isinstance(data, dict)

    def test_multiple_methods_same_path(self, tmp_path: Path) -> None:
        """Test handling multiple HTTP methods on same path."""
        routes = [
            sample_route(path="/pets", method="GET"),
            sample_route(path="/pets", method="POST"),
            sample_route(path="/pets", method="PUT"),
        ]
        generator = UnitTestGenerator(routes=routes)

        result = generator.generate(output_dir=tmp_path)
        test_file = result["test_pets"]

        content = test_file.read_text()

        # Should have tests for all methods
        assert "get" in content.lower()
        assert "post" in content.lower()
        assert "put" in content.lower()
