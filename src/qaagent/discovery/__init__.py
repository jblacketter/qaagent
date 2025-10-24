"""
Route discovery from source code.

Supports auto-discovering API routes from:
- Next.js App Router (src/app/api/*/route.ts)
- FastAPI (future)
- Express (future)
"""

from .nextjs_parser import NextJsRouteDiscoverer

__all__ = ["NextJsRouteDiscoverer"]
