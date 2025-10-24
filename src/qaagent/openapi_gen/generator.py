"""
OpenAPI 3.0 specification generator from discovered routes.

Converts Route objects into valid OpenAPI 3.0 JSON/YAML specifications.
"""

from __future__ import annotations

from typing import Any, Dict, List

from qaagent.analyzers.models import Route


class OpenAPIGenerator:
    """Generates OpenAPI 3.0 specifications from discovered routes."""

    def __init__(
        self,
        routes: List[Route],
        title: str = "API",
        version: str = "1.0.0",
        description: str = "Auto-generated API specification",
    ):
        """
        Initialize the OpenAPI generator.

        Args:
            routes: List of discovered routes
            title: API title
            version: API version
            description: API description
        """
        self.routes = routes
        self.title = title
        self.version = version
        self.description = description

    def generate(self) -> Dict[str, Any]:
        """
        Generate OpenAPI 3.0 specification.

        Returns:
            OpenAPI 3.0 spec as a dictionary
        """
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "paths": self._generate_paths(),
            "components": {
                "schemas": self._generate_schemas(),
                "securitySchemes": self._generate_security_schemes(),
            },
        }

        # Add servers if we can infer them
        servers = self._generate_servers()
        if servers:
            spec["servers"] = servers

        return spec

    def _generate_paths(self) -> Dict[str, Any]:
        """Generate paths section of OpenAPI spec."""
        paths: Dict[str, Any] = {}

        for route in self.routes:
            if route.path not in paths:
                paths[route.path] = {}

            method_lower = route.method.lower()
            paths[route.path][method_lower] = self._generate_operation(route)

        return paths

    def _generate_operation(self, route: Route) -> Dict[str, Any]:
        """Generate operation object for a route."""
        operation: Dict[str, Any] = {
            "summary": route.summary or f"{route.method} {route.path}",
            "tags": route.tags if route.tags else ["api"],
            "responses": self._generate_responses(route),
        }

        # Add description if available
        if route.description:
            operation["description"] = route.description

        # Add parameters
        parameters = self._generate_parameters(route)
        if parameters:
            operation["parameters"] = parameters

        # Add request body for POST/PUT/PATCH
        if route.method in ("POST", "PUT", "PATCH"):
            operation["requestBody"] = self._generate_request_body(route)

        # Add security if auth required
        if route.auth_required:
            operation["security"] = [{"bearerAuth": []}]

        # Add operation ID
        operation_id = self._generate_operation_id(route)
        operation["operationId"] = operation_id

        return operation

    def _generate_parameters(self, route: Route) -> List[Dict[str, Any]]:
        """Generate parameters for a route."""
        parameters = []

        # Path parameters
        if "path" in route.params:
            for param in route.params["path"]:
                param_name = param if isinstance(param, str) else param.get("name")
                parameters.append({
                    "name": param_name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": f"Path parameter: {param_name}",
                })

        # Query parameters
        if "query" in route.params:
            for param in route.params["query"]:
                param_name = param if isinstance(param, str) else param.get("name")
                parameters.append({
                    "name": param_name,
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                    "description": f"Query parameter: {param_name}",
                })

        return parameters

    def _generate_request_body(self, route: Route) -> Dict[str, Any]:
        """Generate request body for POST/PUT/PATCH operations."""
        # Infer schema name from path
        schema_name = self._infer_schema_name_from_path(route.path)

        return {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": f"#/components/schemas/{schema_name}Input"
                    }
                }
            },
        }

    def _generate_responses(self, route: Route) -> Dict[str, Any]:
        """Generate responses for a route."""
        responses: Dict[str, Any] = {}

        # Get expected success status
        if route.method == "POST":
            success_status = "201"
        elif route.method == "DELETE":
            success_status = "204"
        else:
            success_status = "200"

        # Success response
        if success_status in ("200", "201"):
            schema_name = self._infer_schema_name_from_path(route.path)
            responses[success_status] = {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": self._generate_response_schema(route, schema_name)
                    }
                },
            }
        else:
            # 204 No Content
            responses[success_status] = {"description": "No content"}

        # Auth required -> add 401
        if route.auth_required:
            responses["401"] = {"description": "Unauthorized"}

        # Path params -> add 404
        if "{" in route.path:
            responses["404"] = {"description": "Not found"}

        # POST/PUT/PATCH -> add 422
        if route.method in ("POST", "PUT", "PATCH"):
            responses["422"] = {"description": "Validation error"}

        return responses

    def _generate_response_schema(self, route: Route, schema_name: str) -> Dict[str, Any]:
        """Generate response schema based on method and path."""
        # List endpoints (GET without ID) return array
        if route.method == "GET" and "{" not in route.path:
            return {
                "type": "array",
                "items": {"$ref": f"#/components/schemas/{schema_name}"},
            }

        # Single resource endpoints return object
        return {"$ref": f"#/components/schemas/{schema_name}"}

    def _generate_schemas(self) -> Dict[str, Any]:
        """Generate component schemas."""
        schemas: Dict[str, Any] = {}

        # Collect unique schema names from routes
        schema_names = set()
        for route in self.routes:
            schema_name = self._infer_schema_name_from_path(route.path)
            schema_names.add(schema_name)

        # Generate schema for each unique name
        for schema_name in schema_names:
            # Output schema
            schemas[schema_name] = self._generate_basic_schema(schema_name)

            # Input schema (for POST/PUT/PATCH)
            schemas[f"{schema_name}Input"] = self._generate_input_schema(schema_name)

        return schemas

    def _generate_basic_schema(self, schema_name: str) -> Dict[str, Any]:
        """Generate a basic schema for a model."""
        schema_lower = schema_name.lower()

        # Common fields for all schemas
        properties = {
            "id": {"type": "integer", "description": "Unique identifier"},
            "created_at": {
                "type": "string",
                "format": "date-time",
                "description": "Creation timestamp",
            },
            "updated_at": {
                "type": "string",
                "format": "date-time",
                "description": "Last update timestamp",
            },
        }

        # Add model-specific fields
        if schema_lower == "user":
            properties.update({
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
            })
        elif schema_lower == "post":
            properties.update({
                "title": {"type": "string"},
                "content": {"type": "string"},
                "author_id": {"type": "integer"},
            })
        elif schema_lower == "comment":
            properties.update({
                "content": {"type": "string"},
                "post_id": {"type": "integer"},
                "user_id": {"type": "integer"},
            })
        else:
            # Generic schema
            properties.update({
                "name": {"type": "string"},
                "description": {"type": "string"},
            })

        return {
            "type": "object",
            "properties": properties,
            "required": ["id"],
        }

    def _generate_input_schema(self, schema_name: str) -> Dict[str, Any]:
        """Generate input schema (without id, timestamps)."""
        base_schema = self._generate_basic_schema(schema_name)

        # Remove fields that shouldn't be in input
        properties = {
            k: v
            for k, v in base_schema["properties"].items()
            if k not in ("id", "created_at", "updated_at")
        }

        return {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys())[:1] if properties else [],  # Make first field required
        }

    def _generate_security_schemes(self) -> Dict[str, Any]:
        """Generate security schemes."""
        schemes = {}

        # Check if any route requires auth
        has_auth = any(route.auth_required for route in self.routes)

        if has_auth:
            schemes["bearerAuth"] = {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }

        return schemes

    def _generate_servers(self) -> List[Dict[str, Any]]:
        """Generate servers list."""
        # Could be inferred from base_url if we had it
        return [
            {"url": "http://localhost:3000", "description": "Development server"},
            {"url": "https://api.example.com", "description": "Production server"},
        ]

    def _infer_schema_name_from_path(self, path: str) -> str:
        """
        Infer schema name from API path.

        Examples:
        - /users -> User
        - /posts/{id} -> Post
        - /api/v1/comments -> Comment
        """
        # Remove leading/trailing slashes and split
        parts = [p for p in path.split("/") if p and not p.startswith("{")]

        # Get last non-parameter part
        if parts:
            name = parts[-1]
            # Remove plural 's' and capitalize
            if name.endswith("s"):
                name = name[:-1]
            return name.capitalize()

        return "Resource"

    def _generate_operation_id(self, route: Route) -> str:
        """
        Generate operation ID from route.

        Examples:
        - GET /users -> listUsers
        - GET /users/{id} -> getUser
        - POST /users -> createUser
        - PUT /users/{id} -> updateUser
        - DELETE /users/{id} -> deleteUser
        """
        # Get action from method
        action_map = {
            "GET": "get" if "{" in route.path else "list",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        action = action_map.get(route.method, route.method.lower())

        # Get resource name
        schema_name = self._infer_schema_name_from_path(route.path)

        # For list operations, pluralize
        if action == "list":
            return f"{action}{schema_name}s"

        return f"{action}{schema_name}"
