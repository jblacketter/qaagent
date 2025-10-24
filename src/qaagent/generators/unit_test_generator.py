"""
Unit test generator for pytest-based API tests.

Generates pytest test classes with:
- Happy path tests
- Invalid input tests
- Edge case tests (parametrized)
- Mock-based unit tests
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, PackageLoader, select_autoescape

from qaagent.analyzers.models import Route
from qaagent.generators.data_generator import DataGenerator


class UnitTestGenerator:
    """Generates pytest unit tests from discovered routes."""

    def __init__(self, routes: List[Route], base_url: str = "http://localhost:8000"):
        self.routes = routes
        self.base_url = base_url
        self._setup_jinja()

    def _setup_jinja(self) -> None:
        """Initialize Jinja2 environment."""
        self.jinja_env = Environment(
            loader=PackageLoader("qaagent", "templates/unit"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, output_dir: Path) -> Dict[str, Path]:
        """
        Generate pytest unit tests.

        Args:
            output_dir: Directory to write test files

        Returns:
            Dictionary mapping test file types to paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        generated = {}

        # Group routes by resource
        resources = self._group_routes_by_resource()

        # Generate test file for each resource
        for resource_name, resource_routes in resources.items():
            test_file = self._generate_test_file(resource_name, resource_routes, output_dir)
            generated[f"test_{resource_name}"] = test_file

        # Generate conftest.py with fixtures
        conftest_file = self._generate_conftest(output_dir, resources)
        generated["conftest"] = conftest_file

        # Generate __init__.py
        init_file = output_dir / "__init__.py"
        init_file.write_text("# Generated unit tests\n")
        generated["init"] = init_file

        return generated

    def _group_routes_by_resource(self) -> Dict[str, List[Route]]:
        """Group routes by resource name (first path segment)."""
        resources: Dict[str, List[Route]] = {}

        for route in self.routes:
            # Extract resource from path (e.g., /pets/123 -> pets)
            parts = [p for p in route.path.split("/") if p and "{" not in p]
            resource = parts[0] if parts else "root"

            if resource not in resources:
                resources[resource] = []
            resources[resource].append(route)

        return resources

    def _generate_test_file(
        self, resource_name: str, routes: List[Route], output_dir: Path
    ) -> Path:
        """Generate a test file for a resource."""
        template = self.jinja_env.get_template("test_class_enhanced.py.j2")

        # Prepare test cases for each route
        test_cases = []
        for route in routes:
            test_cases.extend(self._create_test_cases(route))

        content = template.render(
            resource_name=resource_name,
            base_url=self.base_url,
            routes=routes,
            test_cases=test_cases,
        )

        test_file = output_dir / f"test_{resource_name}_api.py"
        test_file.write_text(content)
        return test_file

    def _create_test_cases(self, route: Route) -> List[Dict[str, Any]]:
        """Create test cases for a route."""
        cases = []

        # Happy path test
        cases.append({
            "type": "happy_path",
            "name": f"test_{route.method.lower()}_{self._sanitize_path(route.path)}_success",
            "route": route,
            "description": f"Test {route.method} {route.path} succeeds with valid data",
            "expected_status": self._get_expected_status(route.method),
            "test_data": self._generate_test_data(route),
        })

        # Invalid data tests for POST/PUT/PATCH
        if route.method in ["POST", "PUT", "PATCH"]:
            cases.append({
                "type": "invalid_data",
                "name": f"test_{route.method.lower()}_{self._sanitize_path(route.path)}_invalid_data",
                "route": route,
                "description": f"Test {route.method} {route.path} rejects invalid data",
                "expected_status": 422,  # Unprocessable Entity
                "test_data": {},  # Empty data
            })

        # Parametrized edge cases for path parameters
        if "{" in route.path:
            cases.append({
                "type": "parametrized",
                "name": f"test_{route.method.lower()}_{self._sanitize_path(route.path)}_invalid_params",
                "route": route,
                "description": f"Test {route.method} {route.path} with invalid path parameters",
                "parameters": self._generate_invalid_params(route),
            })

        return cases

    def _sanitize_path(self, path: str) -> str:
        """Convert path to valid Python identifier."""
        # /pets/{pet_id} -> pets_pet_id
        return path.replace("/", "_").replace("{", "").replace("}", "").strip("_")

    def _get_expected_status(self, method: str) -> int:
        """Get expected success status code for HTTP method."""
        status_map = {
            "GET": 200,
            "POST": 201,
            "PUT": 200,
            "PATCH": 200,
            "DELETE": 204,
        }
        return status_map.get(method, 200)

    def _generate_test_data(self, route: Route) -> Dict[str, Any]:
        """Generate sample test data for a route."""
        # Extract schema from request body if available
        if route.method in ["POST", "PUT", "PATCH"]:
            # Look for requestBody in OpenAPI metadata
            if "requestBody" in route.metadata:
                return {"name": "Test Item", "description": "Test description"}

        return {}

    def _generate_invalid_params(self, route: Route) -> List[Any]:
        """Generate invalid parameter values for parametrized tests."""
        # Common invalid values for IDs
        return [-1, 0, "invalid", None, ""]

    def _generate_conftest(self, output_dir: Path, resources: Dict[str, List[Route]]) -> Path:
        """Generate conftest.py with pytest fixtures."""
        template = self.jinja_env.get_template("conftest.py.j2")

        # Generate sample data for each resource using DataGenerator
        resource_data = {}
        data_gen = DataGenerator(self.routes)

        for resource_name in resources.keys():
            # Generate realistic sample data for this resource (single record)
            records = data_gen.generate(
                model_name=resource_name.capitalize(),
                count=1,
            )
            # Use the first (and only) record
            resource_data[resource_name] = records[0] if records else {}

        content = template.render(
            base_url=self.base_url,
            resources=resources,
            resource_data=resource_data,
        )

        conftest_file = output_dir / "conftest.py"
        conftest_file.write_text(content)
        return conftest_file

    def _infer_schema_for_resource(self, resource_name: str) -> Dict[str, Any]:
        """Infer schema structure for a resource based on its name."""
        # Common fields for all resources
        schema = {
            "type": "object",
            "properties": {}
        }

        # Add resource-specific fields based on common patterns
        resource_lower = resource_name.lower()

        if resource_lower == "users":
            schema["properties"] = {
                "name": {"type": "string", "faker": "name"},
                "email": {"type": "string", "faker": "email"},
                "username": {"type": "string", "faker": "user_name"},
            }
        elif resource_lower == "posts":
            schema["properties"] = {
                "title": {"type": "string", "faker": "sentence"},
                "content": {"type": "string", "faker": "text"},
                "author_id": {"type": "integer", "faker": "random_int"},
            }
        elif resource_lower == "comments":
            schema["properties"] = {
                "content": {"type": "string", "faker": "text"},
                "post_id": {"type": "integer", "faker": "random_int"},
                "user_id": {"type": "integer", "faker": "random_int"},
            }
        elif resource_lower == "products":
            schema["properties"] = {
                "name": {"type": "string", "faker": "word"},
                "description": {"type": "string", "faker": "text"},
                "price": {"type": "number", "faker": "random_int"},
            }
        else:
            # Generic schema
            schema["properties"] = {
                "name": {"type": "string", "faker": "word"},
                "description": {"type": "string", "faker": "text"},
            }

        return schema
