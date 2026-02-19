"""API routes for Branch Board."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from qaagent.branch import store
from qaagent.branch.models import BranchCard, BranchCardUpdate, BranchStage, TestChecklist

router = APIRouter(tags=["branches"])


@router.get("/branches")
def list_branches(
    repo_id: Optional[str] = None,
    stage: Optional[str] = None,
) -> dict:
    """List tracked branches, optionally filtered by repo and/or stage."""
    stage_filter = None
    if stage:
        try:
            stage_filter = BranchStage(stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")
    cards = store.branch_list(repo_id=repo_id, stage=stage_filter)
    return {"branches": [c.model_dump() for c in cards]}


@router.get("/branches/{branch_id}")
def get_branch(branch_id: int) -> dict:
    """Get a single branch card."""
    card = store.branch_get(branch_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Branch #{branch_id} not found")
    return card.model_dump()


@router.patch("/branches/{branch_id}")
def update_branch(branch_id: int, update: BranchCardUpdate) -> dict:
    """Update user-editable fields on a branch card."""
    if not store.branch_update(branch_id, update):
        raise HTTPException(status_code=404, detail=f"Branch #{branch_id} not found")
    card = store.branch_get(branch_id)
    return card.model_dump()  # type: ignore[union-attr]


@router.delete("/branches/{branch_id}")
def delete_branch(branch_id: int) -> dict:
    """Delete a branch card."""
    if not store.branch_delete(branch_id):
        raise HTTPException(status_code=404, detail=f"Branch #{branch_id} not found")
    return {"status": "deleted", "id": branch_id}


@router.post("/branches/scan")
def scan_branches(
    repo_id: str,
    repo_path: str,
    base_branch: str = "main",
) -> dict:
    """Scan a repository and sync all branch cards."""
    from qaagent.branch.tracker import BranchTracker
    from qaagent import db

    path = Path(repo_path)
    if not (path / ".git").exists():
        raise HTTPException(status_code=400, detail=f"Not a git repository: {repo_path}")

    # Ensure repo exists in DB
    existing = db.repo_get(repo_id)
    if existing is None:
        db.repo_upsert(repo_id, path.name, str(path), repo_type="local")

    tracker = BranchTracker(path, repo_id, base_branch)
    cards = tracker.scan()
    return {"branches": [c.model_dump() for c in cards], "count": len(cards)}


@router.get("/branches/{branch_id}/checklist")
def get_checklist(branch_id: int) -> dict:
    """Get the latest test checklist for a branch."""
    card = store.branch_get(branch_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Branch #{branch_id} not found")
    checklist = store.checklist_get(branch_id)
    if checklist is None:
        return {"checklist": None}
    return {"checklist": checklist.model_dump()}


@router.patch("/branches/checklist-items/{item_id}")
def update_checklist_item(item_id: int, status: str, notes: Optional[str] = None) -> dict:
    """Update a checklist item status."""
    valid_statuses = {"pending", "passed", "failed", "skipped"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if not store.checklist_item_update_status(item_id, status, notes):
        raise HTTPException(status_code=404, detail=f"Checklist item #{item_id} not found")
    return {"status": "updated", "id": item_id}


@router.get("/branches/{branch_id}/test-runs")
def get_test_runs(branch_id: int) -> dict:
    """Get test runs for a branch."""
    card = store.branch_get(branch_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Branch #{branch_id} not found")
    runs = store.test_runs_list(branch_id)
    return {"test_runs": [r.model_dump() for r in runs]}


@router.get("/branches/stages")
def get_stages() -> dict:
    """Get all available lifecycle stages."""
    return {
        "stages": [
            {"value": s.value, "auto": s in (BranchStage.CREATED, BranchStage.ACTIVE, BranchStage.MERGED)}
            for s in BranchStage
        ]
    }
