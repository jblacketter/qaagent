"""Shared authentication middleware for QA Agent FastAPI apps."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from qaagent import db


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce session-based authentication on all requests.

    - If no users exist (first run), skip auth entirely so the frontend
      can redirect to the setup-admin page.
    - Exempt paths (auth endpoints, static assets, etc.) are configurable.
    - ``api_only=True`` returns 401 JSON for all unauthenticated requests.
      ``api_only=False`` redirects non-``/api/`` paths to ``/login``.
    """

    def __init__(
        self,
        app,
        exempt_prefixes: tuple[str, ...] = ("/api/auth/",),
        api_only: bool = False,
    ):
        super().__init__(app)
        self.exempt_prefixes = exempt_prefixes
        self.api_only = api_only

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always allow exempt paths
        if any(path.startswith(p) for p in self.exempt_prefixes):
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
        if self.api_only or path.startswith("/api/"):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)

        # For non-API routes (web UI only), redirect to login
        return JSONResponse(
            status_code=307,
            headers={"Location": "/login"},
            content=None,
        )
