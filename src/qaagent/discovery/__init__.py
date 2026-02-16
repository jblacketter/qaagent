"""
Route discovery from source code.

Supports auto-discovering API routes from:
- Next.js App Router (src/app/api/*/route.ts)
- FastAPI (@app.get, @router.post, etc.)
- Flask (@app.route, @bp.route, etc.)
- Django (urlpatterns, DRF ViewSets)
- Go (net/http, Gin, Echo)
- Ruby (Rails routes, Sinatra)
- Rust (Actix Web, Axum)
"""

from .base import FrameworkParser, RouteParam
from .nextjs_parser import NextJsRouteDiscoverer
from .fastapi_parser import FastAPIParser
from .flask_parser import FlaskParser
from .django_parser import DjangoParser
from .go_parser import GoParser
from .ruby_parser import RubyParser
from .rust_parser import RustParser

__all__ = [
    "FrameworkParser",
    "RouteParam",
    "NextJsRouteDiscoverer",
    "FastAPIParser",
    "FlaskParser",
    "DjangoParser",
    "GoParser",
    "RubyParser",
    "RustParser",
    "get_framework_parser",
]


def get_framework_parser(framework: str) -> FrameworkParser | None:
    """Return the appropriate parser for a detected framework."""
    parsers = {
        "fastapi": FastAPIParser,
        "flask": FlaskParser,
        "django": DjangoParser,
        "nextjs": NextJsRouteDiscoverer,
        "go": GoParser,
        "ruby": RubyParser,
        "rust": RustParser,
    }
    cls = parsers.get(framework)
    return cls() if cls else None
