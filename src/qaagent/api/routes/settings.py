"""API routes for application settings and info."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from qaagent import db
from qaagent.evidence.run_manager import RunManager

router = APIRouter(tags=["settings"])


class AppSettings(BaseModel):
    version: str
    db_path: str
    auth_enabled: bool
    username: str | None = None
    repos_count: int
    runs_count: int


@router.get("/settings")
def get_settings() -> AppSettings:
    """Return application info and settings."""
    # Version from package metadata
    try:
        from importlib.metadata import version
        app_version = version("qaagent")
    except Exception:
        app_version = "dev"

    # DB path
    db_path = db._db_path or db._default_db_path()

    # Auth info
    user_cnt = db.user_count()
    username = db.user_get_first_username() if user_cnt > 0 else None

    # Repos count
    repos = db.repo_list()

    # Runs count
    manager = RunManager()
    runs_count = 0
    if manager.base_dir.exists():
        runs_count = sum(1 for p in manager.base_dir.iterdir() if p.is_dir())

    return AppSettings(
        version=app_version,
        db_path=db_path,
        auth_enabled=user_cnt > 0,
        username=username,
        repos_count=len(repos),
        runs_count=runs_count,
    )


@router.post("/settings/clear-database")
def clear_database() -> dict[str, str]:
    """Reset all repositories, agent configs, and usage data."""
    conn = db.get_db()
    conn.executescript("""
        DELETE FROM branch_checklist_items;
        DELETE FROM branch_checklists;
        DELETE FROM branch_test_runs;
        DELETE FROM branches;
        DELETE FROM repositories;
        DELETE FROM agent_configs;
        DELETE FROM agent_usage;
    """)
    return {"status": "cleared"}
