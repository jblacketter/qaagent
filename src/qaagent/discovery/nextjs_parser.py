"""
Next.js App Router route discovery.

Discovers API routes from Next.js App Router structure:
- src/app/api/**/route.ts
- app/api/**/route.ts

Supports:
- GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS methods
- Dynamic routes: [id], [slug], [...]rest
- Route groups: (group)
- Parallel routes: @folder
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from qaagent.analyzers.models import Route


class NextJsRouteDiscoverer:
    """Discovers API routes from Next.js App Router source code."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.routes: List[Route] = []

    def discover(self) -> List[Route]:
        """
        Discover all API routes in the Next.js project.

        Returns:
            List of Route objects discovered from source code
        """
        self.routes = []

        # Find all route files
        route_files = self._find_route_files()

        # Parse each route file
        for route_file in route_files:
            routes = self._parse_route_file(route_file)
            self.routes.extend(routes)

        return self.routes

    def _find_route_files(self) -> List[Path]:
        """
        Find all route.ts and route.js files in the project.

        Next.js App Router convention:
        - src/app/api/**/route.{ts,js}
        - app/api/**/route.{ts,js}
        """
        route_files = []

        # Check src/app/api first
        src_app_api = self.project_root / "src" / "app" / "api"
        if src_app_api.exists():
            route_files.extend(src_app_api.rglob("route.ts"))
            route_files.extend(src_app_api.rglob("route.js"))

        # Check app/api (root level)
        app_api = self.project_root / "app" / "api"
        if app_api.exists():
            route_files.extend(app_api.rglob("route.ts"))
            route_files.extend(app_api.rglob("route.js"))

        return sorted(route_files)

    def _parse_route_file(self, route_file: Path) -> List[Route]:
        """
        Parse a single route.ts file and extract HTTP handlers.

        Args:
            route_file: Path to route.ts or route.js file

        Returns:
            List of Route objects for each HTTP method handler found
        """
        routes = []

        try:
            content = route_file.read_text(encoding="utf-8")
        except Exception:
            return routes

        # Infer API path from file structure
        api_path = self._infer_path_from_file(route_file)

        # Find HTTP method handlers
        methods = self._extract_http_methods(content)

        # Create Route object for each method
        for method in methods:
            route = Route(
                path=api_path,
                method=method,
                auth_required=self._detect_auth(content),
                summary=f"{method} {api_path}",
                tags=[self._extract_tag_from_path(api_path)],
                params=self._extract_params_from_path(api_path),
                responses={"200": {"description": "Success"}},
                metadata={
                    "source": "nextjs",
                    "file": str(route_file.relative_to(self.project_root)),
                },
            )
            routes.append(route)

        return routes

    def _infer_path_from_file(self, route_file: Path) -> str:
        """
        Infer API path from directory structure.

        Examples:
        - src/app/api/users/route.ts → /users
        - src/app/api/posts/[id]/route.ts → /posts/{id}
        - src/app/api/v1/admin/route.ts → /v1/admin
        - app/api/posts/[slug]/comments/route.ts → /posts/{slug}/comments
        """
        # Find the 'api' directory in the path
        parts = route_file.parts
        try:
            api_index = parts.index("api")
        except ValueError:
            return "/"

        # Get path segments after 'api' directory
        path_parts = parts[api_index + 1 :]

        # Remove 'route.ts' or 'route.js' from the end
        if path_parts and path_parts[-1] in ("route.ts", "route.js"):
            path_parts = path_parts[:-1]

        # Convert to API path
        api_parts = []
        for part in path_parts:
            # Skip route groups (group) and parallel routes @folder
            if part.startswith("(") and part.endswith(")"):
                continue
            if part.startswith("@"):
                continue

            # Convert dynamic segments [param] → {param}
            if part.startswith("[") and part.endswith("]"):
                param_name = part[1:-1]
                # Handle catch-all routes [...param]
                if param_name.startswith("..."):
                    param_name = param_name[3:]
                api_parts.append(f"{{{param_name}}}")
            else:
                api_parts.append(part)

        # Build final path
        path = "/" + "/".join(api_parts) if api_parts else "/"

        return path

    def _extract_http_methods(self, content: str) -> List[str]:
        """
        Extract HTTP method handlers from route file content.

        Looks for exported functions named GET, POST, PUT, PATCH, DELETE, etc.

        Examples:
        - export async function GET(request) { ... }
        - export function POST(req: Request) { ... }
        - export const PUT = async (request: Request) => { ... }
        """
        methods = []

        # Pattern: export (async)? function METHOD(
        # Pattern: export const METHOD =
        http_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

        for method in http_methods:
            # Function declaration: export async function GET(
            pattern1 = rf"export\s+(?:async\s+)?function\s+{method}\s*\("
            # Const assignment: export const GET =
            pattern2 = rf"export\s+const\s+{method}\s*="

            if re.search(pattern1, content) or re.search(pattern2, content):
                methods.append(method)

        return methods

    def _detect_auth(self, content: str) -> bool:
        """
        Detect if route requires authentication.

        Looks for common auth patterns:
        - getServerSession
        - auth() calls
        - headers().get('authorization')
        - cookies().get('token')
        """
        auth_patterns = [
            r"getServerSession",
            r"auth\(\)",
            r"headers\(\)\.get\(['\"]authorization['\"]",
            r"cookies\(\)\.get\(['\"]token['\"]",
            r"@auth",  # Decorators
            r"requireAuth",
            r"isAuthenticated",
        ]

        for pattern in auth_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        return False

    def _extract_tag_from_path(self, path: str) -> str:
        """
        Extract tag from API path for grouping.

        Examples:
        - /users → users
        - /posts/{id} → posts
        - /v1/admin/users → admin
        """
        # Remove leading slash and split
        parts = [p for p in path.split("/") if p and not p.startswith("{")]

        if not parts:
            return "api"

        # Use first non-version part as tag
        for part in parts:
            if not re.match(r"^v\d+$", part):  # Skip version parts like v1, v2
                return part

        return parts[0]

    def _extract_params_from_path(self, path: str) -> dict:
        """
        Extract path parameters from route path.

        Examples:
        - /users/{id} → {"id": {"in": "path", "type": "string"}}
        - /posts/{slug}/comments → {"slug": {"in": "path", "type": "string"}}
        """
        params = {}

        # Find all {param} segments
        param_pattern = r"\{([^}]+)\}"
        matches = re.findall(param_pattern, path)

        for param_name in matches:
            params[param_name] = {
                "in": "path",
                "type": "string",
                "required": True,
                "description": f"Path parameter: {param_name}",
            }

        return params
