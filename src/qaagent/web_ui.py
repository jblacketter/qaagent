"""
Web UI for QA Agent - FastAPI-based graphical interface.

Provides a browser-based alternative to the CLI with:
- Project configuration
- Visual command execution
- Real-time progress updates
- Integrated reports
- Workspace management
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from qaagent import db
from qaagent.config.manager import TargetManager
from qaagent.workspace import Workspace
from qaagent.discovery import NextJsRouteDiscoverer
from qaagent.analyzers.risk_assessment import assess_risks
from qaagent.dashboard import generate_dashboard
from qaagent.openapi_gen import OpenAPIGenerator
from qaagent.generators.unit_test_generator import UnitTestGenerator


app = FastAPI(title="QA Agent Web UI", version="1.0.0")


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

# Paths that never require authentication
_AUTH_EXEMPT_PREFIXES = (
    "/api/auth/",
    "/assets/",
    "/login",
    "/setup-admin",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce session-based authentication on all requests.

    - If no users exist (first run), skip auth entirely so the frontend
      can redirect to the setup-admin page.
    - Exempt paths (auth endpoints, static assets, login/setup pages).
    - WebSocket upgrade requests are exempted (cookie-based auth is
      unreliable during the HTTP->WS upgrade in some clients).
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always allow exempt paths
        if any(path.startswith(p) for p in _AUTH_EXEMPT_PREFIXES):
            return await call_next(request)

        # Allow WebSocket upgrade only on the actual WebSocket path
        if path == "/ws" and request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # If no users configured yet, let everything through
        # (frontend will redirect to /setup-admin)
        if db.user_count() == 0:
            return await call_next(request)

        # Check session cookie
        from qaagent.api.routes.auth import COOKIE_NAME
        token = request.cookies.get(COOKIE_NAME)
        if token:
            info = db.session_validate(token)
            if info:
                return await call_next(request)

        # Unauthenticated
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)

        # For non-API routes, redirect to login
        return JSONResponse(
            status_code=307,
            headers={"Location": "/login"},
            content=None,
        )


app.add_middleware(AuthMiddleware)


# Store active WebSocket connections for real-time updates
active_connections: List[WebSocket] = []

# Mount the React dashboard static files
dashboard_dist = Path(__file__).parent / "dashboard" / "frontend" / "dist"
if dashboard_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(dashboard_dist / "assets")), name="assets")

# Mount API routers used by the React dashboard
from qaagent.api.routes import runs, evidence, repositories, fix, doc, agent, auth, settings
app.include_router(auth.router, prefix="/api")
app.include_router(repositories.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(fix.router, prefix="/api")
app.include_router(doc.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


class TargetInput(BaseModel):
    name: str
    path: str
    is_remote: bool = False


class CommandRequest(BaseModel):
    target: str
    command: str
    params: dict = {}


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the React dashboard."""
    dashboard_index = Path(__file__).parent / "dashboard" / "frontend" / "dist" / "index.html"
    if dashboard_index.exists():
        return FileResponse(dashboard_index)
    return HTMLResponse(
        "<h1>QA Agent Web UI</h1>"
        "<p>React dashboard not built. Run <code>npm run build</code> "
        "in <code>src/qaagent/dashboard/frontend/</code></p>",
        status_code=500,
    )


@app.get("/api/targets")
async def list_targets():
    """Get list of configured targets."""
    manager = TargetManager()
    targets = [
        {
            "name": entry.name,
            "path": str(entry.path),
            "project_type": entry.project_type,
            "is_active": manager.get_active() and manager.get_active().name == entry.name,
        }
        for entry in manager.list_targets()
    ]
    return JSONResponse({"targets": targets})


@app.post("/api/targets")
async def add_target(target_input: TargetInput):
    """Add a new target."""
    try:
        manager = TargetManager()

        # If remote URL, clone first
        if target_input.is_remote:
            from qaagent.repo import RepoCloner
            cloner = RepoCloner()
            local_path = cloner.clone(target_input.path)
            target_path = str(local_path)
        else:
            target_path = target_input.path

        entry = manager.add_target(target_input.name, target_path)
        manager.set_active(target_input.name)

        return JSONResponse({
            "success": True,
            "target": {
                "name": entry.name,
                "path": str(entry.path),
                "project_type": entry.project_type,
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/targets/{target_name}/activate")
async def activate_target(target_name: str):
    """Set a target as active."""
    try:
        manager = TargetManager()
        entry = manager.set_active(target_name)
        return JSONResponse({"success": True, "target": entry.name})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.get("/api/workspace/{target_name}")
async def get_workspace_info(target_name: str):
    """Get workspace information for a target."""
    try:
        ws = Workspace()
        info = ws.get_workspace_info(target_name)
        return JSONResponse(info)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/commands/discover")
async def discover_routes(request: CommandRequest):
    """Discover routes from Next.js source."""
    try:
        await broadcast({"type": "status", "message": "Discovering routes..."})

        manager = TargetManager()
        entry = manager.get(request.target)
        if not entry:
            return JSONResponse({"success": False, "error": "Target not found"}, status_code=404)

        discoverer = NextJsRouteDiscoverer(entry.resolved_path())
        routes = discoverer.discover()

        await broadcast({"type": "status", "message": f"Discovered {len(routes)} routes"})

        return JSONResponse({
            "success": True,
            "routes_count": len(routes),
            "routes": [
                {
                    "path": r.path,
                    "method": r.method,
                    "auth_required": r.auth_required,
                    "tags": r.tags,
                }
                for r in routes[:20]  # First 20 for preview
            ]
        })
    except Exception as e:
        await broadcast({"type": "error", "message": str(e)})
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/commands/generate-openapi")
async def generate_openapi_endpoint(request: CommandRequest):
    """Generate OpenAPI specification."""
    try:
        await broadcast({"type": "status", "message": "Discovering routes..."})

        manager = TargetManager()
        entry = manager.get(request.target)
        if not entry:
            return JSONResponse({"success": False, "error": "Target not found"}, status_code=404)

        # Discover routes
        discoverer = NextJsRouteDiscoverer(entry.resolved_path())
        routes = discoverer.discover()

        await broadcast({"type": "status", "message": f"Generating OpenAPI spec for {len(routes)} routes..."})

        # Generate OpenAPI spec
        generator = OpenAPIGenerator(
            routes=routes,
            title=request.params.get("title", entry.name),
            version=request.params.get("version", "1.0.0"),
        )
        spec = generator.generate()

        # Save to workspace
        ws = Workspace()
        output_file = ws.get_openapi_path(request.target, format="json")
        output_file.write_text(json.dumps(spec, indent=2))

        await broadcast({"type": "success", "message": f"OpenAPI spec generated: {output_file}"})

        return JSONResponse({
            "success": True,
            "file": str(output_file),
            "paths": len(spec["paths"]),
            "schemas": len(spec["components"]["schemas"]),
        })
    except Exception as e:
        await broadcast({"type": "error", "message": str(e)})
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/commands/generate-dashboard")
async def generate_dashboard_endpoint(request: CommandRequest):
    """Generate visual dashboard."""
    try:
        await broadcast({"type": "status", "message": "Analyzing project..."})

        manager = TargetManager()
        entry = manager.get(request.target)
        if not entry:
            return JSONResponse({"success": False, "error": "Target not found"}, status_code=404)

        # Discover routes
        await broadcast({"type": "status", "message": "Discovering routes..."})
        discoverer = NextJsRouteDiscoverer(entry.resolved_path())
        routes = discoverer.discover()

        # Assess risks
        await broadcast({"type": "status", "message": "Assessing risks..."})
        risks = assess_risks(routes)

        # Generate dashboard
        await broadcast({"type": "status", "message": "Generating dashboard..."})
        ws = Workspace()
        dashboard_path = ws.get_reports_dir(request.target) / "dashboard.html"

        generate_dashboard(
            routes=routes,
            risks=risks,
            output_path=dashboard_path,
            title=f"{request.target} QA Dashboard",
            project_name=request.target,
        )

        await broadcast({"type": "success", "message": "Dashboard generated successfully!"})

        return JSONResponse({
            "success": True,
            "file": str(dashboard_path),
            "routes": len(routes),
            "risks": len(risks),
        })
    except Exception as e:
        await broadcast({"type": "error", "message": str(e)})
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/commands/generate-tests")
async def generate_tests_endpoint(request: CommandRequest):
    """Generate unit tests."""
    try:
        await broadcast({"type": "status", "message": "Discovering routes..."})

        manager = TargetManager()
        entry = manager.get(request.target)
        if not entry:
            return JSONResponse({"success": False, "error": "Target not found"}, status_code=404)

        # Discover routes
        discoverer = NextJsRouteDiscoverer(entry.resolved_path())
        routes = discoverer.discover()

        await broadcast({"type": "status", "message": f"Generating tests for {len(routes)} routes..."})

        # Generate tests
        ws = Workspace()
        tests_dir = ws.get_tests_dir(request.target, test_type="unit")

        generator = UnitTestGenerator(routes, base_url=request.params.get("base_url", "http://localhost:3000"))
        generated = generator.generate(tests_dir)

        await broadcast({"type": "success", "message": f"Generated {generated.file_count} test files"})

        return JSONResponse({
            "success": True,
            "files": generated.file_count,
            "directory": str(tests_dir),
        })
    except Exception as e:
        await broadcast({"type": "error", "message": str(e)})
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.get("/api/reports/{target_name}/dashboard")
async def get_dashboard(target_name: str):
    """Serve the dashboard HTML."""
    try:
        ws = Workspace()
        dashboard_path = ws.get_reports_dir(target_name) / "dashboard.html"

        if not dashboard_path.exists():
            return JSONResponse({"error": "Dashboard not found. Generate it first."}, status_code=404)

        return FileResponse(dashboard_path, media_type="text/html")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# Catch-all route for React Router (must be last)
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def catch_all(full_path: str):
    """Serve React app for all non-API routes (for client-side routing)."""
    # Only serve React app for non-API routes
    if not full_path.startswith("api/"):
        dashboard_index = Path(__file__).parent / "dashboard" / "frontend" / "dist" / "index.html"
        if dashboard_index.exists():
            return FileResponse(dashboard_index)

    # If it's an API route that wasn't caught, return 404
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast(message: dict):
    """Broadcast message to all connected WebSocket clients."""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass


def start_web_ui(host: str = "127.0.0.1", port: int = 8080):
    """Start the web UI server."""
    import uvicorn
    print(f"Starting QA Agent Web UI at http://{host}:{port}")
    print(f"Open your browser to: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_web_ui()
