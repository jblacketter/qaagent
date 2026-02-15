"""FastAPI application exposing QA Agent evidence and analysis."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from qaagent.api.routes import runs, evidence, repositories, fix, doc


def create_app() -> FastAPI:
    app = FastAPI(title="QA Agent API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"]
,
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(runs.router, prefix="/api")
    app.include_router(evidence.router, prefix="/api")
    app.include_router(repositories.router, prefix="/api")
    app.include_router(fix.router, prefix="/api")
    app.include_router(doc.router, prefix="/api")
    return app


app = create_app()
