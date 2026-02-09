"""
Route discovery from source code.

Supports auto-discovering API routes from:
- Next.js App Router (src/app/api/*/route.ts)
- FastAPI (@app.get, @router.post, etc.)
- Flask (@app.route, @bp.route, etc.)
- Django (urlpatterns, DRF ViewSets)
"""

from .base import FrameworkParser, RouteParam
from .nextjs_parser import NextJsRouteDiscoverer
from .fastapi_parser import FastAPIParser
from .flask_parser import FlaskParser
from .django_parser import DjangoParser

__all__ = [
    "FrameworkParser",
    "RouteParam",
    "NextJsRouteDiscoverer",
    "FastAPIParser",
    "FlaskParser",
    "DjangoParser",
    "get_framework_parser",
]


def get_framework_parser(framework: str) -> FrameworkParser | None:
    """Return the appropriate parser for a detected framework."""
    parsers = {
        "fastapi": FastAPIParser,
        "flask": FlaskParser,
        "django": DjangoParser,
    }
    cls = parsers.get(framework)
    return cls() if cls else None
