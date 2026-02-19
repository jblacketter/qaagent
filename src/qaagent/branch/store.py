"""SQLite persistence for Branch Board."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from qaagent import db
from qaagent.branch.models import (
    BranchCard,
    BranchCardUpdate,
    BranchStage,
    BranchTestRun,
    ChecklistItem,
    TestChecklist,
)


# ---------------------------------------------------------------------------
# Branch CRUD
# ---------------------------------------------------------------------------


def branch_upsert(card: BranchCard) -> int:
    """Insert or update a branch card. Returns the row id."""
    conn = db.get_db()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO branches
               (repo_id, branch_name, base_branch, stage, story_id, story_url,
                notes, change_summary, commit_count, files_changed,
                first_seen_at, last_updated_at, merged_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(repo_id, branch_name) DO UPDATE SET
               stage = excluded.stage,
               story_id = COALESCE(excluded.story_id, branches.story_id),
               story_url = COALESCE(excluded.story_url, branches.story_url),
               notes = COALESCE(excluded.notes, branches.notes),
               change_summary = excluded.change_summary,
               commit_count = excluded.commit_count,
               files_changed = excluded.files_changed,
               last_updated_at = excluded.last_updated_at,
               merged_at = COALESCE(excluded.merged_at, branches.merged_at)""",
        (
            card.repo_id,
            card.branch_name,
            card.base_branch,
            card.stage.value,
            card.story_id,
            card.story_url,
            card.notes,
            card.change_summary,
            card.commit_count,
            card.files_changed,
            card.first_seen_at or now,
            now,
            card.merged_at,
        ),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def branch_update(branch_id: int, update: BranchCardUpdate) -> bool:
    """Partially update a branch card (user-editable fields). Returns True if found."""
    conn = db.get_db()
    parts: list[str] = []
    params: list = []
    if update.stage is not None:
        parts.append("stage = ?")
        params.append(update.stage.value)
    if update.story_id is not None:
        parts.append("story_id = ?")
        params.append(update.story_id)
    if update.story_url is not None:
        parts.append("story_url = ?")
        params.append(update.story_url)
    if update.notes is not None:
        parts.append("notes = ?")
        params.append(update.notes)
    if not parts:
        return True  # nothing to update
    parts.append("last_updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(branch_id)
    cur = conn.execute(
        f"UPDATE branches SET {', '.join(parts)} WHERE id = ?", params
    )
    conn.commit()
    return cur.rowcount > 0


def branch_get(branch_id: int) -> Optional[BranchCard]:
    """Get a branch card by id."""
    conn = db.get_db()
    row = conn.execute("SELECT * FROM branches WHERE id = ?", (branch_id,)).fetchone()
    return _row_to_card(row) if row else None


def branch_get_by_name(repo_id: str, branch_name: str) -> Optional[BranchCard]:
    """Get a branch card by repo + branch name."""
    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM branches WHERE repo_id = ? AND branch_name = ?",
        (repo_id, branch_name),
    ).fetchone()
    return _row_to_card(row) if row else None


def branch_list(
    repo_id: Optional[str] = None,
    stage: Optional[BranchStage] = None,
) -> list[BranchCard]:
    """List branch cards, optionally filtered by repo and/or stage."""
    conn = db.get_db()
    clauses: list[str] = []
    params: list = []
    if repo_id is not None:
        clauses.append("repo_id = ?")
        params.append(repo_id)
    if stage is not None:
        clauses.append("stage = ?")
        params.append(stage.value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM branches{where} ORDER BY last_updated_at DESC", params
    ).fetchall()
    return [_row_to_card(r) for r in rows]


def branch_delete(branch_id: int) -> bool:
    """Delete a branch card (checklists/runs cascade via FK)."""
    conn = db.get_db()
    cur = conn.execute("DELETE FROM branches WHERE id = ?", (branch_id,))
    conn.commit()
    return cur.rowcount > 0


def _row_to_card(row) -> BranchCard:
    return BranchCard(
        id=row["id"],
        repo_id=row["repo_id"],
        branch_name=row["branch_name"],
        base_branch=row["base_branch"],
        stage=BranchStage(row["stage"]),
        story_id=row["story_id"],
        story_url=row["story_url"],
        notes=row["notes"],
        change_summary=row["change_summary"],
        commit_count=row["commit_count"],
        files_changed=row["files_changed"],
        first_seen_at=row["first_seen_at"],
        last_updated_at=row["last_updated_at"],
        merged_at=row["merged_at"],
    )


# ---------------------------------------------------------------------------
# Checklist CRUD
# ---------------------------------------------------------------------------


def checklist_create(checklist: TestChecklist) -> int:
    """Create a checklist and its items. Returns checklist id."""
    conn = db.get_db()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO branch_checklists (branch_id, generated_at, format, source_diff)
           VALUES (?, ?, ?, ?)""",
        (checklist.branch_id, now, checklist.format, checklist.source_diff_hash),
    )
    checklist_id = cur.lastrowid
    for item in checklist.items:
        conn.execute(
            """INSERT INTO branch_checklist_items
                   (checklist_id, description, category, priority, status, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (checklist_id, item.description, item.category, item.priority, item.status, item.notes),
        )
    conn.commit()
    return checklist_id  # type: ignore[return-value]


def checklist_get(branch_id: int) -> Optional[TestChecklist]:
    """Get the latest checklist for a branch, with items."""
    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM branch_checklists WHERE branch_id = ? ORDER BY generated_at DESC LIMIT 1",
        (branch_id,),
    ).fetchone()
    if row is None:
        return None
    checklist_id = row["id"]
    items = conn.execute(
        "SELECT * FROM branch_checklist_items WHERE checklist_id = ? ORDER BY id",
        (checklist_id,),
    ).fetchall()
    return TestChecklist(
        id=row["id"],
        branch_id=row["branch_id"],
        generated_at=row["generated_at"],
        format=row["format"],
        source_diff_hash=row["source_diff"],
        items=[
            ChecklistItem(
                id=i["id"],
                checklist_id=i["checklist_id"],
                description=i["description"],
                category=i["category"],
                priority=i["priority"],
                status=i["status"],
                notes=i["notes"],
            )
            for i in items
        ],
    )


def checklist_item_update_status(item_id: int, status: str, notes: Optional[str] = None) -> bool:
    """Update status of a single checklist item."""
    conn = db.get_db()
    if notes is not None:
        cur = conn.execute(
            "UPDATE branch_checklist_items SET status = ?, notes = ? WHERE id = ?",
            (status, notes, item_id),
        )
    else:
        cur = conn.execute(
            "UPDATE branch_checklist_items SET status = ? WHERE id = ?",
            (status, item_id),
        )
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Test run CRUD
# ---------------------------------------------------------------------------


def test_run_create(run: BranchTestRun) -> int:
    """Record a test run for a branch. Returns run id."""
    conn = db.get_db()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO branch_test_runs
               (branch_id, run_id, suite_type, total, passed, failed, skipped,
                promoted_to_regression, run_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run.branch_id,
            run.run_id,
            run.suite_type,
            run.total,
            run.passed,
            run.failed,
            run.skipped,
            run.promoted_to_regression,
            run.run_at or now,
        ),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def test_run_promote(run_db_id: int) -> bool:
    """Mark a test run as promoted to regression. Returns True if found."""
    conn = db.get_db()
    cur = conn.execute(
        "UPDATE branch_test_runs SET promoted_to_regression = 1 WHERE id = ?",
        (run_db_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def test_runs_list(branch_id: int) -> list[BranchTestRun]:
    """List test runs for a branch."""
    conn = db.get_db()
    rows = conn.execute(
        "SELECT * FROM branch_test_runs WHERE branch_id = ? ORDER BY run_at DESC",
        (branch_id,),
    ).fetchall()
    return [
        BranchTestRun(
            id=r["id"],
            branch_id=r["branch_id"],
            run_id=r["run_id"],
            suite_type=r["suite_type"],
            total=r["total"],
            passed=r["passed"],
            failed=r["failed"],
            skipped=r["skipped"],
            promoted_to_regression=bool(r["promoted_to_regression"]),
            run_at=r["run_at"],
        )
        for r in rows
    ]
