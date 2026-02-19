"""Pydantic models for Branch Board."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BranchStage(str, enum.Enum):
    """Lifecycle stages for a branch card.

    Automatic transitions (via git polling):
        created -> active -> in_review -> merged
    Manual transitions only:
        merged -> qa -> released
    """

    CREATED = "created"
    ACTIVE = "active"
    IN_REVIEW = "in_review"
    MERGED = "merged"
    QA = "qa"
    RELEASED = "released"


class StoryLink(BaseModel):
    """Association between a branch and a story/ticket."""

    story_id: str  # e.g., "PROJ-123"
    story_url: Optional[str] = None  # e.g., "https://jira.example.com/browse/PROJ-123"


class BranchCard(BaseModel):
    """A branch card representing a tracked branch in the board."""

    id: int = 0
    repo_id: str
    branch_name: str
    base_branch: str = "main"
    stage: BranchStage = BranchStage.CREATED
    story_id: Optional[str] = None
    story_url: Optional[str] = None
    notes: Optional[str] = None
    change_summary: Optional[str] = None
    commit_count: int = 0
    files_changed: int = 0
    first_seen_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    merged_at: Optional[str] = None


class BranchCardUpdate(BaseModel):
    """Partial update for a branch card (user-editable fields)."""

    stage: Optional[BranchStage] = None
    story_id: Optional[str] = None
    story_url: Optional[str] = None
    notes: Optional[str] = None


class ChecklistItem(BaseModel):
    """A single test checklist item."""

    id: int = 0
    checklist_id: int = 0
    description: str
    category: Optional[str] = None  # route_change, security, edge_case
    priority: str = "medium"  # high, medium, low
    status: str = "pending"  # pending, passed, failed, skipped
    notes: Optional[str] = None


class TestChecklist(BaseModel):
    """A test checklist generated for a branch."""

    id: int = 0
    branch_id: int = 0
    generated_at: Optional[str] = None
    format: str = "checklist"  # checklist or gherkin (future)
    source_diff_hash: Optional[str] = None
    items: list[ChecklistItem] = Field(default_factory=list)


class BranchTestRun(BaseModel):
    """A test run associated with a branch."""

    id: int = 0
    branch_id: int = 0
    run_id: Optional[str] = None
    suite_type: Optional[str] = None  # pytest, behave, playwright
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    promoted_to_regression: bool = False
    run_at: Optional[str] = None
