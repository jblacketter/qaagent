"""Test executor — generates and runs tests scoped to branch changes."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path


BRANCH_TESTS_DIR = Path.home() / ".qaagent" / "branch-tests"


def _posix(path: str) -> str:
    """Normalize a file path to POSIX-style forward slashes."""
    return path.replace("\\", "/")


@dataclass
class BranchGenerationResult:
    """Result of generating tests for a branch."""

    files_generated: int = 0
    test_count: int = 0
    output_dir: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class BranchRunResult:
    """Result of running tests for a branch."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    suite_type: str = "pytest"
    run_id: str = ""


def generate_branch_tests(
    repo_path: Path,
    branch_name: str,
    branch_id: int,
    base_branch: str = "main",
    base_url: str = "http://localhost:8000",
) -> BranchGenerationResult:
    """Generate unit tests for routes changed in a branch.

    Pipeline:
    1. Analyze branch diff to find changed route files
    2. Discover all routes from repo source code
    3. Filter routes to those in changed files
    4. Generate pytest tests for filtered routes
    """
    from qaagent.analyzers.route_discovery import discover_routes
    from qaagent.branch.diff_analyzer import DiffAnalyzer
    from qaagent.generators.unit_test_generator import UnitTestGenerator

    # 1. Analyze diff
    analyzer = DiffAnalyzer(repo_path, base_branch)
    diff = analyzer.analyze(branch_name)

    # Prefer route files; fall back to all non-test changed files.
    # Normalize to POSIX paths so git diff output (forward slashes)
    # matches route metadata (platform separators on Windows).
    changed_paths = {_posix(fc.path) for fc in diff.route_files}
    if not changed_paths:
        test_paths = {_posix(f.path) for f in diff.test_files}
        changed_paths = {
            _posix(fc.path)
            for fc in diff.files
            if _posix(fc.path) not in test_paths
        }

    warnings: list[str] = []

    if not changed_paths:
        return BranchGenerationResult(
            warnings=["No changed files found in branch diff"],
        )

    # 2. Discover routes from source
    all_routes = discover_routes(source_path=str(repo_path))

    if not all_routes:
        return BranchGenerationResult(
            warnings=["No routes discovered from source code"],
        )

    # 3. Filter routes to changed files (normalize metadata paths too)
    filtered = [
        r for r in all_routes
        if _posix(r.metadata.get("file", "")) in changed_paths
    ]

    if not filtered:
        # Fallback: OpenAPI-sourced routes lack file metadata
        if diff.route_files:
            filtered = all_routes
            warnings.append(
                f"Could not filter routes by file; using all {len(all_routes)} routes"
            )
        else:
            return BranchGenerationResult(
                warnings=["No routes match the changed files"],
            )

    # 4. Generate tests
    output_dir = BRANCH_TESTS_DIR / str(branch_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = UnitTestGenerator(
        routes=filtered,
        base_url=base_url,
        output_dir=output_dir,
        project_name=repo_path.name,
    )
    result = generator.generate()

    return BranchGenerationResult(
        files_generated=result.stats.get("files", len(result.files)),
        test_count=result.stats.get("tests", 0),
        output_dir=str(output_dir),
        warnings=warnings + result.warnings,
    )


def run_branch_tests(branch_id: int) -> BranchRunResult:
    """Run previously generated tests for a branch.

    Returns:
        BranchRunResult with pass/fail counts.

    Raises:
        FileNotFoundError: If no tests have been generated for this branch.
    """
    from qaagent.runners.pytest_runner import PytestRunner

    test_dir = BRANCH_TESTS_DIR / str(branch_id)
    if not test_dir.exists() or not any(test_dir.glob("test_*.py")):
        raise FileNotFoundError(
            f"No generated tests found for branch {branch_id}. "
            "Generate tests first."
        )

    runner = PytestRunner(output_dir=test_dir)
    result = runner.run(test_dir)

    run_id = (
        f"branch-{branch_id}-"
        f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    )

    return BranchRunResult(
        total=result.total,
        passed=result.passed,
        failed=result.failed,
        skipped=result.skipped,
        suite_type="pytest",
        run_id=run_id,
    )
