"""Checklist generator — produces test checklists from branch diff analysis."""

from __future__ import annotations

from qaagent.branch.diff_analyzer import DiffResult, FileChange
from qaagent.branch.models import ChecklistItem, TestChecklist


def generate_checklist(diff: DiffResult, branch_id: int = 0) -> TestChecklist:
    """Generate a test checklist from a diff analysis result.

    Produces checklist items categorized by:
    - route_change: API/route files changed
    - data_integrity: migration or model files changed
    - config: configuration files changed
    - regression: existing test files changed (verify they still pass)
    - new_code: new files added that need test coverage
    - edge_case: files with large diffs that need careful review

    Args:
        diff: The DiffResult from DiffAnalyzer.
        branch_id: The branch card ID to associate the checklist with.

    Returns:
        A TestChecklist with generated items.
    """
    items: list[ChecklistItem] = []

    # Route changes — high priority
    for fc in diff.route_files:
        items.extend(_items_for_route_change(fc))

    # Migration / data changes — high priority
    for fc in diff.migration_files:
        items.append(ChecklistItem(
            description=f"Verify migration '{_short_path(fc.path)}' applies cleanly and is reversible",
            category="data_integrity",
            priority="high",
        ))
        items.append(ChecklistItem(
            description=f"Verify data integrity after migration '{_short_path(fc.path)}'",
            category="data_integrity",
            priority="high",
        ))

    # Config changes — medium priority
    for fc in diff.config_files:
        items.append(ChecklistItem(
            description=f"Verify config change in '{_short_path(fc.path)}' does not break existing behavior",
            category="config",
            priority="medium",
        ))
        if _is_ci_config(fc.path):
            items.append(ChecklistItem(
                description=f"Verify CI/CD pipeline still passes after changes to '{_short_path(fc.path)}'",
                category="config",
                priority="high",
            ))

    # Test file changes — verify regressions
    for fc in diff.test_files:
        if fc.status == "added":
            items.append(ChecklistItem(
                description=f"Run new test file '{_short_path(fc.path)}' and verify all tests pass",
                category="regression",
                priority="medium",
            ))
        elif fc.status == "modified":
            items.append(ChecklistItem(
                description=f"Verify modified tests in '{_short_path(fc.path)}' still pass",
                category="regression",
                priority="medium",
            ))
        elif fc.status == "deleted":
            items.append(ChecklistItem(
                description=f"Confirm test file '{_short_path(fc.path)}' was intentionally removed and coverage is not reduced",
                category="regression",
                priority="high",
            ))

    # New non-test, non-route files — need coverage
    for fc in diff.other_files:
        if fc.status == "added":
            items.append(ChecklistItem(
                description=f"Verify new file '{_short_path(fc.path)}' has adequate test coverage",
                category="new_code",
                priority="medium",
            ))

    # Large diffs — edge case review
    for fc in diff.files:
        if fc.additions + fc.deletions > 100:
            items.append(ChecklistItem(
                description=f"Review large change in '{_short_path(fc.path)}' ({fc.additions}+/{fc.deletions}- lines) for edge cases",
                category="edge_case",
                priority="medium",
            ))

    # Summary items based on overall diff
    if diff.route_files:
        items.append(ChecklistItem(
            description="Run full API integration test suite to verify no route regressions",
            category="regression",
            priority="high",
        ))

    if not items:
        items.append(ChecklistItem(
            description="No significant changes detected — verify branch builds and passes existing tests",
            category="regression",
            priority="low",
        ))

    return TestChecklist(
        branch_id=branch_id,
        format="checklist",
        source_diff_hash=diff.diff_hash,
        items=items,
    )


def _items_for_route_change(fc: FileChange) -> list[ChecklistItem]:
    """Generate checklist items for a changed route file."""
    short = _short_path(fc.path)
    items: list[ChecklistItem] = []

    if fc.status == "added":
        items.append(ChecklistItem(
            description=f"Test all new endpoints in '{short}' with valid inputs",
            category="route_change",
            priority="high",
        ))
        items.append(ChecklistItem(
            description=f"Test new endpoints in '{short}' with invalid/edge-case inputs",
            category="route_change",
            priority="high",
        ))
        items.append(ChecklistItem(
            description=f"Verify authentication/authorization on new endpoints in '{short}'",
            category="route_change",
            priority="high",
        ))
    elif fc.status == "modified":
        items.append(ChecklistItem(
            description=f"Verify modified endpoints in '{short}' still return expected responses",
            category="route_change",
            priority="high",
        ))
        items.append(ChecklistItem(
            description=f"Test modified endpoints in '{short}' with edge-case inputs",
            category="route_change",
            priority="medium",
        ))
    elif fc.status == "deleted":
        items.append(ChecklistItem(
            description=f"Confirm removed routes from '{short}' are no longer referenced by clients",
            category="route_change",
            priority="high",
        ))

    return items


def _short_path(path: str) -> str:
    """Shorten a file path for display (last 3 segments)."""
    parts = path.replace("\\", "/").split("/")
    if len(parts) > 3:
        return ".../" + "/".join(parts[-3:])
    return path


def _is_ci_config(path: str) -> bool:
    """Check if a file is a CI/CD configuration file."""
    lower = path.lower()
    return any(p in lower for p in (
        ".github/", ".gitlab-ci", "jenkinsfile", "makefile",
        "docker-compose", "dockerfile",
    ))
