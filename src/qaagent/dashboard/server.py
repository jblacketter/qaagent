"""Simple helper to serve the built dashboard via uvicorn."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from qaagent.api.app import create_app


def create_dashboard_app(dist_dir: Path | None = None) -> FastAPI:
    api_app = create_app()
    dist = dist_dir or Path(__file__).parent / "frontend" / "dist"
    if not dist.exists():
        raise RuntimeError(f"Dashboard build not found at {dist}. Run 'npm run build' inside frontend/ first.")

    api_app.mount("/dashboard", StaticFiles(directory=dist, html=True), name="dashboard")
    return api_app
