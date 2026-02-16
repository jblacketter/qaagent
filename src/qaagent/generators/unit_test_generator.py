"""
Unit test generator for pytest-based API tests.

Generates pytest test classes with:
- Happy path tests
- Invalid input tests
- Edge case tests (parametrized)
- Mock-based unit tests
- LLM-enhanced assertions and edge cases (when enabled)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, PackageLoader, select_autoescape

from qaagent.analyzers.models import Risk, Route
from qaagent.config.models import LLMSettings
from qaagent.generators.base import BaseGenerator, GenerationResult, validate_python_syntax
from qaagent.generators.data_generator import DataGenerator
from qaagent.generators.validator import TestValidator


class UnitTestGenerator(BaseGenerator):
    """Generates pytest unit tests from discovered routes."""

    def __init__(
        self,
        routes: List[Route],
        base_url: str = "http://localhost:8000",
        risks: Optional[List[Risk]] = None,
        output_dir: Optional[Path] = None,
        project_name: str = "Application",
        llm_settings: Optional[LLMSettings] = None,
        retrieval_context: Optional[List[str]] = None,
    ):
        super().__init__(
            routes=routes,
            risks=risks,
            output_dir=output_dir,
            base_url=base_url,
            project_name=project_name,
            llm_settings=llm_settings,
            retrieval_context=retrieval_context,
        )
        self._setup_jinja()
        self._enhancer = None
        self._validator = TestValidator()

    def _get_enhancer(self):
        """Lazy-init LLM enhancer."""
        if self._enhancer is None and self.llm_enabled:
            from qaagent.generators.llm_enhancer import LLMTestEnhancer
            self._enhancer = LLMTestEnhancer(self.llm_settings)
        return self._enhancer

    def _setup_jinja(self) -> None:
        """Initialize Jinja2 environment."""
        self.jinja_env = Environment(
            loader=PackageLoader("qaagent", "templates/unit"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, output_dir: Optional[Path] = None, **kwargs) -> GenerationResult:
        """
        Generate pytest unit tests.

        Args:
            output_dir: Directory to write test files (overrides constructor value)

        Returns:
            GenerationResult with files, stats, and warnings
        """
        target_dir = Path(output_dir) if output_dir else self.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        result = GenerationResult()
        test_count = 0

        # Group routes by resource
        resources = self._group_routes_by_resource()

        # Generate test file for each resource
        for resource_name, resource_routes in resources.items():
            test_file, count = self._generate_test_file(resource_name, resource_routes, target_dir, result)
            result.files[f"test_{resource_name}"] = test_file
            test_count += count

        # Generate conftest.py with fixtures
        conftest_file = self._generate_conftest(target_dir, resources)
        result.files["conftest"] = conftest_file

        # Generate __init__.py
        init_file = target_dir / "__init__.py"
        init_file.write_text("# Generated unit tests\n")
        result.files["init"] = init_file

        result.stats = {
            "tests": test_count,
            "files": len(result.files),
            "resources": len(resources),
        }
        result.llm_used = self.llm_enabled and self._enhancer is not None

        return result

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
        self, resource_name: str, routes: List[Route], output_dir: Path, result: GenerationResult
    ) -> tuple[Path, int]:
        """Generate a test file for a resource. Returns (path, test_count)."""
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

        # Validate syntax and attempt LLM fix
        content, was_fixed = self._validator.validate_and_fix(
            content, "python", enhancer=self._get_enhancer(), max_retries=2,
        )
        vr = self._validator.validate_python(content)
        if not vr.valid:
            result.warnings.append(f"test_{resource_name}_api.py has syntax error: {'; '.join(vr.errors)}")

        test_file = output_dir / f"test_{resource_name}_api.py"
        test_file.write_text(content)
        return test_file, len(test_cases)

    def _create_test_cases(self, route: Route) -> List[Dict[str, Any]]:
        """Create test cases for a route."""
        cases = []

        # LLM-enhanced assertions
        extra_assertions = []
        enhancer = self._get_enhancer()
        if enhancer:
            schema = self._extract_response_schema(route)
            extra_assertions = enhancer.enhance_assertions(
                route,
                schema,
                retrieval_context=self.retrieval_context,
            )

        # Happy path test — use concrete sample path for parameterized routes
        sample_path = self._resolve_sample_path(route.path)

        cases.append({
            "type": "happy_path",
            "name": f"test_{route.method.lower()}_{self._sanitize_path(route.path)}_success",
            "route": route,
            "sample_path": sample_path,
            "description": f"Test {route.method} {route.path} succeeds with valid data",
            "expected_status": self._get_expected_status(route.method),
            "test_data": self._generate_test_data(route),
            "extra_assertions": extra_assertions,
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
            edge_params = self._generate_invalid_params(route)
            cases.append({
                "type": "parametrized",
                "name": f"test_{route.method.lower()}_{self._sanitize_path(route.path)}_invalid_params",
                "route": route,
                "description": f"Test {route.method} {route.path} with invalid path parameters",
                "parameters": edge_params,
            })

        return cases

    @staticmethod
    def _resolve_sample_path(path: str) -> str:
        """Replace path parameters with concrete sample values for happy-path tests.

        E.g. /pets/{pet_id} -> /pets/1, /users/{user_id}/posts/{post_id} -> /users/1/posts/1
        """
        import re
        return re.sub(r"\{[^}]+\}", "1", path)

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
        """Generate invalid parameter values for parametrized tests.

        LLM returns list[dict] with {name, params, expected_status, description}.
        Template needs scalar values for path interpolation, so we extract the
        first value from each case's params dict.
        """
        enhancer = self._get_enhancer()
        if enhancer:
            cases = enhancer.generate_edge_cases(
                route,
                self.risks,
                retrieval_context=self.retrieval_context,
            )
            if cases:
                return self._normalize_edge_cases(cases)

        # Template fallback: common invalid values for IDs
        return [-1, 0, "invalid", None, ""]

    @staticmethod
    def _normalize_edge_cases(cases: List[Any]) -> List[Any]:
        """Extract scalar param values from LLM-returned edge case dicts."""
        scalars = []
        for case in cases:
            if isinstance(case, dict) and "params" in case:
                params = case["params"]
                if isinstance(params, dict) and params:
                    # Take the first param value
                    scalars.append(next(iter(params.values())))
                else:
                    scalars.append(params)
            else:
                # Already a scalar (from fallback)
                scalars.append(case)
        return scalars if scalars else [-1, 0, "invalid", None, ""]

    def _extract_response_schema(self, route: Route) -> Optional[Dict[str, Any]]:
        """Extract response schema from route responses."""
        for status_code, response_data in route.responses.items():
            if isinstance(response_data, dict):
                content = response_data.get("content", {})
                json_content = content.get("application/json", {})
                schema = json_content.get("schema")
                if schema:
                    return schema
        return None

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
