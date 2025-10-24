"""
OpenAPI specification generator from discovered routes.

Generates OpenAPI 3.0 specs from:
- Next.js App Router routes
- FastAPI routes (future)
- Express routes (future)
"""

from .generator import OpenAPIGenerator

__all__ = ["OpenAPIGenerator"]
