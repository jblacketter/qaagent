"""Unit tests for Next.js route discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from qaagent.discovery.nextjs_parser import NextJsRouteDiscoverer


class TestNextJsRouteDiscoverer:
    """Test suite for Next.js route discovery."""

    def test_infer_path_simple(self, tmp_path: Path) -> None:
        """Test path inference for simple routes."""
        discoverer = NextJsRouteDiscoverer(tmp_path)

        # Create: src/app/api/users/route.ts
        route_file = tmp_path / "src" / "app" / "api" / "users" / "route.ts"
        path = discoverer._infer_path_from_file(route_file)

        assert path == "/users"

    def test_infer_path_nested(self, tmp_path: Path) -> None:
        """Test path inference for nested routes."""
        discoverer = NextJsRouteDiscoverer(tmp_path)

        # Create: src/app/api/v1/admin/users/route.ts
        route_file = tmp_path / "src" / "app" / "api" / "v1" / "admin" / "users" / "route.ts"
        path = discoverer._infer_path_from_file(route_file)

        assert path == "/v1/admin/users"

    def test_infer_path_dynamic_segment(self, tmp_path: Path) -> None:
        """Test path inference for dynamic routes."""
        discoverer = NextJsRouteDiscoverer(tmp_path)

        # Create: src/app/api/posts/[id]/route.ts
        route_file = tmp_path / "src" / "app" / "api" / "posts" / "[id]" / "route.ts"
        path = discoverer._infer_path_from_file(route_file)

        assert path == "/posts/{id}"

    def test_infer_path_multiple_dynamic_segments(self, tmp_path: Path) -> None:
        """Test path inference for multiple dynamic segments."""
        discoverer = NextJsRouteDiscoverer(tmp_path)

        # Create: src/app/api/users/[userId]/posts/[postId]/route.ts
        route_file = (
            tmp_path
            / "src"
            / "app"
            / "api"
            / "users"
            / "[userId]"
            / "posts"
            / "[postId]"
            / "route.ts"
        )
        path = discoverer._infer_path_from_file(route_file)

        assert path == "/users/{userId}/posts/{postId}"

    def test_infer_path_catch_all(self, tmp_path: Path) -> None:
        """Test path inference for catch-all routes."""
        discoverer = NextJsRouteDiscoverer(tmp_path)

        # Create: src/app/api/files/[...path]/route.ts
        route_file = tmp_path / "src" / "app" / "api" / "files" / "[...path]" / "route.ts"
        path = discoverer._infer_path_from_file(route_file)

        assert path == "/files/{path}"

    def test_infer_path_route_group(self, tmp_path: Path) -> None:
        """Test that route groups are ignored."""
        discoverer = NextJsRouteDiscoverer(tmp_path)

        # Create: src/app/api/(auth)/login/route.ts
        route_file = tmp_path / "src" / "app" / "api" / "(auth)" / "login" / "route.ts"
        path = discoverer._infer_path_from_file(route_file)

        assert path == "/login"  # (auth) is ignored

    def test_infer_path_app_root(self, tmp_path: Path) -> None:
        """Test path inference for app/ (non-src) structure."""
        discoverer = NextJsRouteDiscoverer(tmp_path)

        # Create: app/api/health/route.ts
        route_file = tmp_path / "app" / "api" / "health" / "route.ts"
        path = discoverer._infer_path_from_file(route_file)

        assert path == "/health"

    def test_extract_http_methods_function_declaration(self) -> None:
        """Test extracting HTTP methods from function declarations."""
        discoverer = NextJsRouteDiscoverer(Path("."))

        content = """
        export async function GET(request) {
            return Response.json({ message: 'Hello' });
        }

        export function POST(request: Request) {
            return new Response('Created', { status: 201 });
        }
        """

        methods = discoverer._extract_http_methods(content)

        assert "GET" in methods
        assert "POST" in methods
        assert len(methods) == 2

    def test_extract_http_methods_arrow_function(self) -> None:
        """Test extracting HTTP methods from arrow functions."""
        discoverer = NextJsRouteDiscoverer(Path("."))

        content = """
        export const PUT = async (request: Request) => {
            return Response.json({ updated: true });
        };

        export const DELETE = (req) => {
            return new Response(null, { status: 204 });
        };
        """

        methods = discoverer._extract_http_methods(content)

        assert "PUT" in methods
        assert "DELETE" in methods

    def test_extract_http_methods_all_methods(self) -> None:
        """Test extracting all supported HTTP methods."""
        discoverer = NextJsRouteDiscoverer(Path("."))

        content = """
        export async function GET(request) {}
        export function POST(request) {}
        export const PUT = async (request) => {};
        export const PATCH = (request) => {};
        export function DELETE(request) {}
        export const HEAD = (request) => {};
        export function OPTIONS(request) {}
        """

        methods = discoverer._extract_http_methods(content)

        assert set(methods) == {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

    def test_detect_auth_get_server_session(self) -> None:
        """Test auth detection with getServerSession."""
        discoverer = NextJsRouteDiscoverer(Path("."))

        content = """
        import { getServerSession } from 'next-auth';

        export async function GET(request) {
            const session = await getServerSession();
            if (!session) {
                return new Response('Unauthorized', { status: 401 });
            }
            return Response.json({ user: session.user });
        }
        """

        assert discoverer._detect_auth(content) is True

    def test_detect_auth_headers(self) -> None:
        """Test auth detection with headers check."""
        discoverer = NextJsRouteDiscoverer(Path("."))

        content = """
        export async function POST(request) {
            const authHeader = headers().get('authorization');
            if (!authHeader) {
                return new Response('Unauthorized', { status: 401 });
            }
            return Response.json({ success: true });
        }
        """

        assert discoverer._detect_auth(content) is True

    def test_detect_auth_no_auth(self) -> None:
        """Test that routes without auth are detected correctly."""
        discoverer = NextJsRouteDiscoverer(Path("."))

        content = """
        export async function GET(request) {
            return Response.json({ public: true });
        }
        """

        assert discoverer._detect_auth(content) is False

    def test_extract_tag_from_path(self) -> None:
        """Test tag extraction from paths."""
        discoverer = NextJsRouteDiscoverer(Path("."))

        assert discoverer._extract_tag("/users") == "users"
        assert discoverer._extract_tag("/posts/{id}") == "posts"
        assert discoverer._extract_tag("/v1/admin/settings") == "admin"
        assert discoverer._extract_tag("/") == "api"

    def test_extract_params_from_path(self) -> None:
        """Test parameter extraction from paths."""
        discoverer = NextJsRouteDiscoverer(Path("."))

        # Single param
        params = discoverer._extract_path_params("/users/{id}")
        assert len(params) == 1
        assert params[0].name == "id"
        assert params[0].required is True

        # Multiple params
        params = discoverer._extract_path_params("/users/{userId}/posts/{postId}")
        names = {p.name for p in params}
        assert "userId" in names
        assert "postId" in names

        # No params
        params = discoverer._extract_path_params("/health")
        assert len(params) == 0

    def test_find_route_files_src_structure(self, tmp_path: Path) -> None:
        """Test finding route files in src/app/api structure."""
        # Create src/app/api structure
        api_dir = tmp_path / "src" / "app" / "api"
        api_dir.mkdir(parents=True)

        # Create route files
        (api_dir / "users" / "route.ts").parent.mkdir()
        (api_dir / "users" / "route.ts").write_text("export function GET() {}")

        (api_dir / "posts" / "route.ts").parent.mkdir()
        (api_dir / "posts" / "route.ts").write_text("export function GET() {}")

        discoverer = NextJsRouteDiscoverer(tmp_path)
        route_files = discoverer.find_route_files(tmp_path)

        assert len(route_files) == 2
        assert any("users" in str(f) for f in route_files)
        assert any("posts" in str(f) for f in route_files)

    def test_find_route_files_app_structure(self, tmp_path: Path) -> None:
        """Test finding route files in app/api structure (no src)."""
        # Create app/api structure
        api_dir = tmp_path / "app" / "api"
        api_dir.mkdir(parents=True)

        # Create route file
        (api_dir / "health" / "route.ts").parent.mkdir()
        (api_dir / "health" / "route.ts").write_text("export function GET() {}")

        discoverer = NextJsRouteDiscoverer(tmp_path)
        route_files = discoverer.find_route_files(tmp_path)

        assert len(route_files) == 1
        assert "health" in str(route_files[0])

    def test_parse_route_file(self, tmp_path: Path) -> None:
        """Test parsing a complete route file."""
        # Create route file
        route_file = tmp_path / "src" / "app" / "api" / "users" / "route.ts"
        route_file.parent.mkdir(parents=True)
        route_file.write_text("""
        export async function GET(request) {
            return Response.json({ users: [] });
        }

        export async function POST(request) {
            const data = await request.json();
            return Response.json({ id: 1, ...data }, { status: 201 });
        }
        """)

        discoverer = NextJsRouteDiscoverer(tmp_path)
        routes = discoverer._parse_route_file(route_file)

        assert len(routes) == 2

        get_route = next(r for r in routes if r.method == "GET")
        assert get_route.path == "/users"
        assert get_route.summary == "GET /users"
        assert "users" in get_route.tags

        post_route = next(r for r in routes if r.method == "POST")
        assert post_route.path == "/users"
        assert post_route.method == "POST"

    def test_discover_integration(self, tmp_path: Path) -> None:
        """Test full discovery workflow."""
        # Create Next.js structure
        api_dir = tmp_path / "src" / "app" / "api"

        # users route
        users_route = api_dir / "users" / "route.ts"
        users_route.parent.mkdir(parents=True)
        users_route.write_text("export function GET() {}")

        # posts/[id] route
        post_route = api_dir / "posts" / "[id]" / "route.ts"
        post_route.parent.mkdir(parents=True)
        post_route.write_text("""
        export function GET() {}
        export function PUT() {}
        export function DELETE() {}
        """)

        # Discover all routes
        discoverer = NextJsRouteDiscoverer(tmp_path)
        routes = discoverer.discover()

        assert len(routes) == 4  # 1 from users, 3 from posts/[id]

        # Check users route
        users_routes = [r for r in routes if r.path == "/users"]
        assert len(users_routes) == 1
        assert users_routes[0].method == "GET"

        # Check posts routes
        posts_routes = [r for r in routes if r.path == "/posts/{id}"]
        assert len(posts_routes) == 3
        methods = {r.method for r in posts_routes}
        assert methods == {"GET", "PUT", "DELETE"}

        # Check metadata
        assert all(r.metadata.get("source") == "nextjs" for r in routes)
