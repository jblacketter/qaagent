"""
Unit tests for OpenAPIGenerator
"""

from __future__ import annotations

import pytest

from qaagent.analyzers.models import Route, RouteSource
from qaagent.openapi_gen import OpenAPIGenerator


class TestOpenAPIGenerator:
    """Tests for OpenAPI 3.0 specification generator."""

    @pytest.fixture
    def sample_routes(self):
        """Sample routes for testing."""
        return [
            Route(
                path="/users",
                method="GET",
                auth_required=False,
                source=RouteSource.CODE,
                tags=["users"],
                summary="List all users",
            ),
            Route(
                path="/users/{id}",
                method="GET",
                auth_required=False,
                source=RouteSource.CODE,
                tags=["users"],
                summary="Get user by ID",
                params={"path": ["id"]},
            ),
            Route(
                path="/users",
                method="POST",
                auth_required=False,
                source=RouteSource.CODE,
                tags=["users"],
                summary="Create new user",
            ),
            Route(
                path="/users/{id}",
                method="PUT",
                auth_required=False,
                source=RouteSource.CODE,
                tags=["users"],
                summary="Update user",
                params={"path": ["id"]},
            ),
            Route(
                path="/users/{id}",
                method="DELETE",
                auth_required=False,
                source=RouteSource.CODE,
                tags=["users"],
                summary="Delete user",
                params={"path": ["id"]},
            ),
        ]

    @pytest.fixture
    def generator(self, sample_routes):
        """Generator fixture."""
        return OpenAPIGenerator(
            routes=sample_routes,
            title="Test API",
            version="1.0.0",
            description="Test API description",
        )

    def test_generator_initialization(self, sample_routes):
        """Test generator can be initialized."""
        gen = OpenAPIGenerator(
            routes=sample_routes,
            title="My API",
            version="2.0.0",
        )
        assert gen.routes == sample_routes
        assert gen.title == "My API"
        assert gen.version == "2.0.0"

    def test_generate_returns_valid_spec(self, generator):
        """Test that generate() returns a valid OpenAPI 3.0 spec."""
        spec = generator.generate()

        # Check top-level structure
        assert spec["openapi"] == "3.0.3"
        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "1.0.0"
        assert spec["info"]["description"] == "Test API description"
        assert "paths" in spec
        assert "components" in spec

    def test_paths_generated_correctly(self, generator):
        """Test that paths are generated correctly."""
        spec = generator.generate()
        paths = spec["paths"]

        # Should have 2 paths
        assert "/users" in paths
        assert "/users/{id}" in paths

        # /users should have GET and POST
        assert "get" in paths["/users"]
        assert "post" in paths["/users"]

        # /users/{id} should have GET, PUT, DELETE
        assert "get" in paths["/users/{id}"]
        assert "put" in paths["/users/{id}"]
        assert "delete" in paths["/users/{id}"]

    def test_operation_has_required_fields(self, generator):
        """Test that operations have all required fields."""
        spec = generator.generate()
        operation = spec["paths"]["/users"]["get"]

        # Required fields
        assert "summary" in operation
        assert "tags" in operation
        assert "responses" in operation
        assert "operationId" in operation

    def test_operation_id_generation(self, generator):
        """Test operation ID generation."""
        spec = generator.generate()

        # List operations
        assert spec["paths"]["/users"]["get"]["operationId"] == "listUsers"

        # Single resource operations
        assert spec["paths"]["/users/{id}"]["get"]["operationId"] == "getUser"
        assert spec["paths"]["/users"]["post"]["operationId"] == "createUser"
        assert spec["paths"]["/users/{id}"]["put"]["operationId"] == "updateUser"
        assert spec["paths"]["/users/{id}"]["delete"]["operationId"] == "deleteUser"

    def test_parameters_for_path_params(self, generator):
        """Test that path parameters are generated correctly."""
        spec = generator.generate()
        operation = spec["paths"]["/users/{id}"]["get"]

        assert "parameters" in operation
        params = operation["parameters"]
        assert len(params) == 1

        param = params[0]
        assert param["name"] == "id"
        assert param["in"] == "path"
        assert param["required"] is True
        assert param["schema"]["type"] == "string"

    def test_request_body_for_post(self, generator):
        """Test that POST operations have request bodies."""
        spec = generator.generate()
        operation = spec["paths"]["/users"]["post"]

        assert "requestBody" in operation
        body = operation["requestBody"]
        assert body["required"] is True
        assert "application/json" in body["content"]
        assert "$ref" in body["content"]["application/json"]["schema"]

    def test_request_body_for_put(self, generator):
        """Test that PUT operations have request bodies."""
        spec = generator.generate()
        operation = spec["paths"]["/users/{id}"]["put"]

        assert "requestBody" in operation

    def test_no_request_body_for_get(self, generator):
        """Test that GET operations don't have request bodies."""
        spec = generator.generate()
        operation = spec["paths"]["/users"]["get"]

        assert "requestBody" not in operation

    def test_responses_for_get(self, generator):
        """Test response generation for GET."""
        spec = generator.generate()
        operation = spec["paths"]["/users"]["get"]

        assert "200" in operation["responses"]
        response = operation["responses"]["200"]
        assert "description" in response
        assert "content" in response
        assert "application/json" in response["content"]

    def test_responses_for_post(self, generator):
        """Test response generation for POST."""
        spec = generator.generate()
        operation = spec["paths"]["/users"]["post"]

        # POST should return 201
        assert "201" in operation["responses"]
        # Should also have 422 for validation errors
        assert "422" in operation["responses"]

    def test_responses_for_delete(self, generator):
        """Test response generation for DELETE."""
        spec = generator.generate()
        operation = spec["paths"]["/users/{id}"]["delete"]

        # DELETE should return 204
        assert "204" in operation["responses"]
        # Should also have 404 (path params present)
        assert "404" in operation["responses"]

    def test_list_endpoint_returns_array(self, generator):
        """Test that list endpoints return arrays."""
        spec = generator.generate()
        operation = spec["paths"]["/users"]["get"]
        schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

        assert schema["type"] == "array"
        assert "items" in schema
        assert "$ref" in schema["items"]

    def test_single_resource_returns_object(self, generator):
        """Test that single resource endpoints return objects."""
        spec = generator.generate()
        operation = spec["paths"]["/users/{id}"]["get"]
        schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

        assert "$ref" in schema

    def test_schemas_generated(self, generator):
        """Test that component schemas are generated."""
        spec = generator.generate()
        schemas = spec["components"]["schemas"]

        # Should have User and UserInput schemas
        assert "User" in schemas
        assert "UserInput" in schemas

    def test_user_schema_structure(self, generator):
        """Test User schema has correct structure."""
        spec = generator.generate()
        schema = spec["components"]["schemas"]["User"]

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "id" in schema["properties"]
        assert "name" in schema["properties"]
        assert "email" in schema["properties"]
        assert "created_at" in schema["properties"]
        assert "updated_at" in schema["properties"]

    def test_input_schema_excludes_readonly_fields(self, generator):
        """Test that input schemas exclude id and timestamps."""
        spec = generator.generate()
        schema = spec["components"]["schemas"]["UserInput"]

        properties = schema["properties"]
        assert "id" not in properties
        assert "created_at" not in properties
        assert "updated_at" not in properties
        # But should have other fields
        assert "name" in properties
        assert "email" in properties

    def test_auth_required_adds_401_response(self):
        """Test that auth_required routes have 401 response."""
        routes = [
            Route(
                path="/protected",
                method="GET",
                auth_required=True,
                source=RouteSource.CODE,
            ),
        ]
        gen = OpenAPIGenerator(routes=routes)
        spec = gen.generate()

        operation = spec["paths"]["/protected"]["get"]
        assert "401" in operation["responses"]
        assert "security" in operation

    def test_security_schemes_when_auth_present(self):
        """Test security schemes are added when auth is required."""
        routes = [
            Route(
                path="/protected",
                method="GET",
                auth_required=True,
                source=RouteSource.CODE,
            ),
        ]
        gen = OpenAPIGenerator(routes=routes)
        spec = gen.generate()

        assert "securitySchemes" in spec["components"]
        assert "bearerAuth" in spec["components"]["securitySchemes"]
        scheme = spec["components"]["securitySchemes"]["bearerAuth"]
        assert scheme["type"] == "http"
        assert scheme["scheme"] == "bearer"

    def test_no_security_schemes_without_auth(self, generator):
        """Test no security schemes when no auth required."""
        spec = generator.generate()

        # Our sample routes don't have auth
        assert len(spec["components"]["securitySchemes"]) == 0

    def test_schema_inference_from_path(self, generator):
        """Test schema name inference from path."""
        # Test various paths
        assert generator._infer_schema_name_from_path("/users") == "User"
        assert generator._infer_schema_name_from_path("/posts") == "Post"
        assert generator._infer_schema_name_from_path("/comments") == "Comment"
        assert generator._infer_schema_name_from_path("/users/{id}") == "User"
        assert generator._infer_schema_name_from_path("/api/v1/users") == "User"

    def test_servers_included(self, generator):
        """Test that servers are included in spec."""
        spec = generator.generate()

        assert "servers" in spec
        assert len(spec["servers"]) > 0
        assert "url" in spec["servers"][0]

    def test_multiple_resources(self):
        """Test generation with multiple different resources."""
        routes = [
            Route(path="/users", method="GET", auth_required=False, source=RouteSource.CODE),
            Route(path="/posts", method="GET", auth_required=False, source=RouteSource.CODE),
            Route(path="/comments", method="GET", auth_required=False, source=RouteSource.CODE),
        ]
        gen = OpenAPIGenerator(routes=routes)
        spec = gen.generate()

        # Should have all paths
        assert "/users" in spec["paths"]
        assert "/posts" in spec["paths"]
        assert "/comments" in spec["paths"]

        # Should have all schemas
        schemas = spec["components"]["schemas"]
        assert "User" in schemas
        assert "Post" in schemas
        assert "Comment" in schemas

    def test_query_parameters(self):
        """Test that query parameters are generated."""
        routes = [
            Route(
                path="/users",
                method="GET",
                auth_required=False,
                source=RouteSource.CODE,
                params={"query": ["page", "limit"]},
            ),
        ]
        gen = OpenAPIGenerator(routes=routes)
        spec = gen.generate()

        operation = spec["paths"]["/users"]["get"]
        params = operation["parameters"]

        assert len(params) == 2
        param_names = [p["name"] for p in params]
        assert "page" in param_names
        assert "limit" in param_names

        # Query params should not be required
        for param in params:
            if param["in"] == "query":
                assert param["required"] is False

    def test_default_values(self):
        """Test default values when not specified."""
        routes = [Route(path="/test", method="GET", auth_required=False, source=RouteSource.CODE)]
        gen = OpenAPIGenerator(routes=routes)

        assert gen.title == "API"
        assert gen.version == "1.0.0"
        assert gen.description == "Auto-generated API specification"

    def test_empty_routes_list(self):
        """Test handling of empty routes list."""
        gen = OpenAPIGenerator(routes=[])
        spec = gen.generate()

        assert spec["paths"] == {}
        assert len(spec["components"]["schemas"]) == 0

    def test_patch_method(self):
        """Test PATCH method handling."""
        routes = [
            Route(
                path="/users/{id}",
                method="PATCH",
                auth_required=False,
                source=RouteSource.CODE,
                params={"path": ["id"]},
            ),
        ]
        gen = OpenAPIGenerator(routes=routes)
        spec = gen.generate()

        operation = spec["paths"]["/users/{id}"]["patch"]
        assert "requestBody" in operation
        assert "200" in operation["responses"]
        assert "422" in operation["responses"]
        assert operation["operationId"] == "updateUser"
