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


@router.post("/branches/{branch_id}/checklist/generate")
def generate_checklist_endpoint(branch_id: int) -> dict:
    """Generate a test checklist from the branch diff."""
    from qaagent.branch.diff_analyzer import DiffAnalyzer
    from qaagent.branch.checklist_generator import generate_checklist
    from qaagent import db

    card = store.branch_get(branch_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Branch #{branch_id} not found")

    # Look up repo path
    repo = db.repo_get(card.repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"Repository '{card.repo_id}' not found")

    repo_path = Path(repo["path"])
    if not (repo_path / ".git").exists():
        raise HTTPException(status_code=400, detail=f"Not a git repository: {repo['path']}")

    analyzer = DiffAnalyzer(repo_path, card.base_branch)
    diff = analyzer.analyze(card.branch_name)
    checklist = generate_checklist(diff, branch_id=card.id)
    store.checklist_create(checklist)

    return {
        "checklist": checklist.model_dump(),
        "diff_summary": {
            "total_files": len(diff.files),
            "route_files": len(diff.route_files),
            "test_files": len(diff.test_files),
            "config_files": len(diff.config_files),
            "migration_files": len(diff.migration_files),
            "additions": diff.total_additions,
            "deletions": diff.total_deletions,
        },
    }


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


@router.post("/branches/{branch_id}/generate-tests")
def generate_tests_endpoint(
    branch_id: int,
    base_url: str = "http://localhost:8000",
) -> dict:
    """Generate automated tests from routes changed in the branch."""
    from qaagent.branch.test_executor import generate_branch_tests
    from qaagent import db

    card = store.branch_get(branch_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Branch #{branch_id} not found")

    repo = db.repo_get(card.repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"Repository '{card.repo_id}' not found")

    repo_path = Path(repo["path"])
    if not (repo_path / ".git").exists():
        raise HTTPException(status_code=400, detail=f"Not a git repository: {repo['path']}")

    try:
        result = generate_branch_tests(
            repo_path=repo_path,
            branch_name=card.branch_name,
            branch_id=card.id,
            base_branch=card.base_branch,
            base_url=base_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test generation failed: {e}")

    return {
        "files_generated": result.files_generated,
        "test_count": result.test_count,
        "output_dir": result.output_dir,
        "warnings": result.warnings,
    }


@router.post("/branches/{branch_id}/run-tests")
def run_tests_endpoint(branch_id: int) -> dict:
    """Run previously generated tests for a branch."""
    from qaagent.branch.test_executor import run_branch_tests
    from qaagent.branch.models import BranchTestRun

    card = store.branch_get(branch_id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Branch #{branch_id} not found")

    try:
        result = run_branch_tests(card.id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test run failed: {e}")

    # Store the run
    run = BranchTestRun(
        branch_id=card.id,
        run_id=result.run_id,
        suite_type=result.suite_type,
        total=result.total,
        passed=result.passed,
        failed=result.failed,
        skipped=result.skipped,
    )
    store.test_run_create(run)

    return {
        "test_run": run.model_dump(),
        "summary": {
            "total": result.total,
            "passed": result.passed,
            "failed": result.failed,
            "skipped": result.skipped,
        },
    }


@router.patch("/branches/test-runs/{run_db_id}/promote")
def promote_test_run(run_db_id: int) -> dict:
    """Mark a test run as promoted to regression suite."""
    if not store.test_run_promote(run_db_id):
        raise HTTPException(status_code=404, detail=f"Test run #{run_db_id} not found")
    return {"status": "promoted", "id": run_db_id}


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
