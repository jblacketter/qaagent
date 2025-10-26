"""API routes for repository management."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from qaagent.evidence.run_manager import RunManager


router = APIRouter(tags=["repositories"])


class RepositoryCreate(BaseModel):
    """Repository creation request."""
    name: str
    path: str
    repo_type: str  # "local" or "github"
    analysis_options: dict[str, bool]


class Repository(BaseModel):
    """Repository metadata."""
    id: str
    name: str
    path: str
    repo_type: str
    last_scan: Optional[str] = None
    status: str = "ready"  # "ready", "analyzing", "error"
    run_count: int = 0
    analysis_options: dict[str, bool]


class AnalyzeRequest(BaseModel):
    """Request to analyze a repository."""
    force: bool = False


# Simple in-memory storage for now
# TODO: Replace with persistent storage (SQLite, JSON file, etc.)
repositories: dict[str, Repository] = {}


@router.get("/repositories")
def list_repositories() -> dict[str, list[Repository]]:
    """List all configured repositories."""
    return {"repositories": list(repositories.values())}


@router.post("/repositories")
def create_repository(repo: RepositoryCreate) -> Repository:
    """Add a new repository for analysis."""
    # Generate a simple ID from the name
    repo_id = repo.name.lower().replace(" ", "-")

    # Check if repository already exists
    if repo_id in repositories:
        raise HTTPException(status_code=400, detail=f"Repository '{repo.name}' already exists")

    # Validate path exists for local repositories
    if repo.repo_type == "local":
        repo_path = Path(repo.path)
        if not repo_path.exists():
            raise HTTPException(status_code=400, detail=f"Path does not exist: {repo.path}")
        if not repo_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {repo.path}")

    # Create repository entry
    new_repo = Repository(
        id=repo_id,
        name=repo.name,
        path=repo.path,
        repo_type=repo.repo_type,
        analysis_options=repo.analysis_options,
    )

    repositories[repo_id] = new_repo
    return new_repo


@router.get("/repositories/{repo_id}")
def get_repository(repo_id: str) -> Repository:
    """Get repository details."""
    if repo_id not in repositories:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")
    return repositories[repo_id]


@router.delete("/repositories/{repo_id}")
def delete_repository(repo_id: str) -> dict[str, str]:
    """Delete a repository."""
    if repo_id not in repositories:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")

    del repositories[repo_id]
    return {"status": "deleted", "id": repo_id}


@router.post("/repositories/{repo_id}/analyze")
def analyze_repository(repo_id: str, request: AnalyzeRequest) -> dict[str, str]:
    """Trigger analysis for a repository."""
    if repo_id not in repositories:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")

    repo = repositories[repo_id]

    # Update status to analyzing
    repo.status = "analyzing"

    try:
        # Change to repository directory
        repo_path = Path(repo.path)

        # Run qaagent analyze commands based on options
        commands = []

        if repo.analysis_options.get("testCoverage") or repo.analysis_options.get("codeQuality"):
            commands.append(["qaagent", "analyze", "collectors"])

        if repo.analysis_options.get("security") or repo.analysis_options.get("performance"):
            commands.append(["qaagent", "analyze", "risks"])

        # Execute commands
        for cmd in commands:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                repo.status = "error"
                raise HTTPException(
                    status_code=500,
                    detail=f"Analysis failed: {result.stderr}"
                )

        # Update repository metadata
        repo.status = "ready"
        repo.last_scan = datetime.now().isoformat()
        repo.run_count += 1

        return {
            "status": "completed",
            "repo_id": repo_id,
            "message": "Analysis completed successfully"
        }

    except subprocess.TimeoutExpired:
        repo.status = "error"
        raise HTTPException(status_code=500, detail="Analysis timed out after 5 minutes")
    except Exception as e:
        repo.status = "error"
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/repositories/{repo_id}/status")
def get_repository_status(repo_id: str) -> dict[str, str]:
    """Get the current analysis status of a repository."""
    if repo_id not in repositories:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")

    repo = repositories[repo_id]
    return {
        "repo_id": repo_id,
        "status": repo.status,
        "last_scan": repo.last_scan or "never",
    }


@router.get("/repositories/{repo_id}/runs")
def get_repository_runs(repo_id: str, limit: int = 10) -> dict:
    """Get analysis runs for a repository."""
    if repo_id not in repositories:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")

    repo = repositories[repo_id]

    # Get runs from RunManager for this repository path
    # For now, return all runs - we'll filter by repo in the future
    manager = RunManager()
    runs_root = manager.base_dir
    run_ids = sorted(
        [p.name for p in runs_root.iterdir() if p.is_dir()],
        reverse=True
    )[:limit]

    runs = []
    for run_id in run_ids:
        handle = manager.load_run(run_id)
        # TODO: Filter by repository path/target
        runs.append(handle.manifest.to_dict())

    return {
        "repo_id": repo_id,
        "runs": runs,
        "total": len(run_ids),
    }
