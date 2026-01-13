"""API routes for auto-fix functionality."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from qaagent.autofix import AutoFixer
from qaagent.evidence.run_manager import RunManager
from qaagent.analyzers.evidence_reader import EvidenceReader
from qaagent.collectors.flake8 import Flake8Collector, Flake8Config
from qaagent.evidence import EvidenceWriter, EvidenceIDGenerator

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["fix"])


class FixableCategory(BaseModel):
    """A category of fixable issues."""
    category: str
    tool: str
    file_count: int
    issue_count: int
    auto_fixable: bool
    severity_breakdown: dict[str, int]
    description: str


class FixableIssuesSummary(BaseModel):
    """Summary of all fixable issues for a repository."""
    categories: list[FixableCategory]
    total_fixable_files: int
    total_fixable_issues: int
    total_manual_files: int


class ApplyFixRequest(BaseModel):
    """Request to apply fixes."""
    category: str
    tool: str
    files: list[str] | None = None


class ApplyFixResponse(BaseModel):
    """Response from applying fixes."""
    status: str
    files_modified: int
    files_failed: int
    message: str
    errors: list[str] = []


@router.get("/runs/{run_id}/fixable-issues")
def get_fixable_issues(run_id: str) -> FixableIssuesSummary:
    """
    Get summary of fixable issues by category for a specific run.

    Groups issues by tool/category and returns counts.
    """
    run_mgr = RunManager()
    try:
        run_handle = run_mgr.load_run(run_id)
        reader = EvidenceReader(run_handle)
        findings = reader.read_findings()

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    except Exception as e:
        LOGGER.error(f"Failed to read findings: {e}")
        return FixableIssuesSummary(
            categories=[],
            total_fixable_files=0,
            total_fixable_issues=0,
            total_manual_files=0,
        )

    # Group findings by tool and severity
    tool_stats = {}
    for finding in findings:
        tool = finding.tool
        if tool not in tool_stats:
            tool_stats[tool] = {
                "files": set(),
                "count": 0,
                "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0, "warning": 0, "error": 0}
            }

        tool_stats[tool]["files"].add(finding.file)
        tool_stats[tool]["count"] += 1

        severity = str(finding.severity).lower()
        if severity in tool_stats[tool]["severity_breakdown"]:
            tool_stats[tool]["severity_breakdown"][severity] += 1
        else:
            # Default to warning for unknown severities
            tool_stats[tool]["severity_breakdown"]["warning"] += 1

    # Build category list
    categories = []

    # Formatting issues (autopep8/black)
    if "flake8" in tool_stats:
        stats = tool_stats["flake8"]
        categories.append(FixableCategory(
            category="formatting",
            tool="autopep8",
            file_count=len(stats["files"]),
            issue_count=stats["count"],
            auto_fixable=True,
            severity_breakdown=stats["severity_breakdown"],
            description="PEP 8 violations: line length, whitespace, indentation"
        ))

    # Note: Import ordering (isort) category removed because we cannot accurately
    # detect import ordering issues from flake8 output alone. Most import-related
    # flake8 errors (F401 unused imports, F403 star imports, etc.) require manual
    # review and cannot be auto-fixed by isort.

    # Security issues (requires manual review)
    if "bandit" in tool_stats:
        stats = tool_stats["bandit"]
        categories.append(FixableCategory(
            category="security",
            tool="bandit",
            file_count=len(stats["files"]),
            issue_count=stats["count"],
            auto_fixable=False,  # Requires LLM or manual review
            severity_breakdown=stats["severity_breakdown"],
            description="Potential security vulnerabilities (requires review)"
        ))

    # Calculate totals
    total_fixable_files = sum(
        cat.file_count for cat in categories if cat.auto_fixable
    )
    total_fixable_issues = sum(
        cat.issue_count for cat in categories if cat.auto_fixable
    )
    total_manual_files = sum(
        cat.file_count for cat in categories if not cat.auto_fixable
    )

    return FixableIssuesSummary(
        categories=categories,
        total_fixable_files=total_fixable_files,
        total_fixable_issues=total_fixable_issues,
        total_manual_files=total_manual_files,
    )


@router.post("/runs/{run_id}/apply-fix")
def apply_fix(run_id: str, request: ApplyFixRequest) -> ApplyFixResponse:
    """
    Apply fixes for a specific run.

    Runs the appropriate auto-fix tool on the repository path from the run and returns results.
    """
    run_mgr = RunManager()
    try:
        run_handle = run_mgr.load_run(run_id)
        repo_path = Path(run_handle.manifest.target.path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    except Exception as e:
        LOGGER.error(f"Failed to load run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load run: {str(e)}")

    # Validate category
    if request.category not in ("formatting", "all"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {request.category}. Must be 'formatting' or 'all'"
        )

    # Initialize auto-fixer
    fixer = AutoFixer(repo_path)

    # Apply fixes based on category
    try:
        errors = []
        files_modified = 0

        if request.category == "formatting" or request.category == "all":
            result = fixer.fix_formatting(request.tool)
            if result.success:
                files_modified += result.files_modified
            else:
                errors.extend(result.errors)

        # Re-run flake8 to update evidence with post-fix counts
        if files_modified > 0:
            try:
                LOGGER.info(f"Re-running flake8 to update evidence after fixes")
                writer = EvidenceWriter(run_handle.evidence_dir)
                id_generator = EvidenceIDGenerator(run_id=run_id)

                # Configure flake8 with longer timeout for large codebases
                flake8_config = Flake8Config(timeout=600)  # 10 minutes
                collector = Flake8Collector(config=flake8_config)

                # Run flake8 - this will overwrite the existing evidence
                collector.run(run_handle, writer, id_generator)
                LOGGER.info(f"Successfully updated evidence with new flake8 results")
            except Exception as e:
                # Don't fail the whole operation if rescan fails
                LOGGER.warning(f"Failed to re-run flake8 after fixes: {e}")
                errors.append(f"Warning: Could not update issue counts automatically: {str(e)}")

        if files_modified > 0:
            return ApplyFixResponse(
                status="success",
                files_modified=files_modified,
                files_failed=len(errors),
                message=f"Fixed {files_modified} files successfully",
                errors=errors,
            )
        else:
            return ApplyFixResponse(
                status="no_changes",
                files_modified=0,
                files_failed=len(errors),
                message="No fixes needed or all files already compliant",
                errors=errors,
            )

    except Exception as e:
        LOGGER.error(f"Fix failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply fixes: {str(e)}"
        )
