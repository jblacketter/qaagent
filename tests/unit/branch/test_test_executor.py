"""Tests for branch test executor — path normalization and pipeline logic."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qaagent.branch.test_executor import (
    _posix,
    generate_branch_tests,
    run_branch_tests,
    BRANCH_TESTS_DIR,
)
from qaagent.branch.diff_analyzer import DiffResult, FileChange


# ---------------------------------------------------------------------------
# _posix() — path normalization regression tests
# ---------------------------------------------------------------------------


class TestPosixNormalization:
    """Ensure path separator normalization works for cross-platform filtering."""

    def test_forward_slashes_unchanged(self):
        assert _posix("src/api/users.py") == "src/api/users.py"

    def test_backslashes_converted(self):
        assert _posix("src\\api\\users.py") == "src/api/users.py"

    def test_mixed_slashes(self):
        assert _posix("src\\api/users.py") == "src/api/users.py"

    def test_empty_string(self):
        assert _posix("") == ""

    def test_windows_route_metadata_matches_git_diff(self):
        """Regression: Windows route metadata (backslash) must match git diff (forward slash)."""
        git_diff_path = "src/api/users.py"
        windows_metadata_path = "src\\api\\users.py"
        assert _posix(git_diff_path) == _posix(windows_metadata_path)


# ---------------------------------------------------------------------------
# generate_branch_tests() — mocked pipeline tests
#
# Imports inside generate_branch_tests() are lazy, so we patch at the
# original module locations rather than on test_executor.
# ---------------------------------------------------------------------------


def _make_diff(
    route_files=None,
    test_files=None,
    other_files=None,
) -> DiffResult:
    all_files = []
    for group in (route_files, test_files, other_files):
        if group:
            all_files.extend(group)
    return DiffResult(
        branch_name="feature/test",
        base_branch="main",
        files=all_files,
        diff_hash="abc123",
        route_files=route_files or [],
        test_files=test_files or [],
        config_files=[],
        migration_files=[],
        other_files=other_files or [],
    )


_PATCH_ANALYZER = "qaagent.branch.diff_analyzer.DiffAnalyzer"
_PATCH_DISCOVER = "qaagent.analyzers.route_discovery.discover_routes"
_PATCH_GENERATOR = "qaagent.generators.unit_test_generator.UnitTestGenerator"


class TestGenerateBranchTests:
    """Tests for the generate_branch_tests pipeline (mocked dependencies)."""

    @patch(_PATCH_ANALYZER)
    def test_no_changed_files_returns_warning(self, mock_analyzer_cls):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_diff()
        mock_analyzer_cls.return_value = mock_analyzer

        result = generate_branch_tests(
            repo_path=MagicMock(),
            branch_name="feature/empty",
            branch_id=1,
        )
        assert result.files_generated == 0
        assert any("No changed files" in w for w in result.warnings)

    @patch(_PATCH_DISCOVER)
    @patch(_PATCH_ANALYZER)
    def test_no_routes_discovered_returns_warning(self, mock_analyzer_cls, mock_discover):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_diff(
            route_files=[FileChange(path="src/api/users.py", additions=10, status="modified")]
        )
        mock_analyzer_cls.return_value = mock_analyzer
        mock_discover.return_value = []

        result = generate_branch_tests(
            repo_path=MagicMock(),
            branch_name="feature/routes",
            branch_id=2,
        )
        assert result.files_generated == 0
        assert any("No routes discovered" in w for w in result.warnings)

    @patch(_PATCH_GENERATOR)
    @patch(_PATCH_DISCOVER)
    @patch(_PATCH_ANALYZER)
    def test_routes_filtered_by_changed_files(self, mock_analyzer_cls, mock_discover, mock_gen_cls):
        """Routes are filtered to those whose metadata['file'] matches changed paths."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_diff(
            route_files=[FileChange(path="src/api/users.py", additions=10, status="modified")]
        )
        mock_analyzer_cls.return_value = mock_analyzer

        # Two routes: one in changed file, one not
        route_match = MagicMock()
        route_match.metadata = {"file": "src/api/users.py"}
        route_no_match = MagicMock()
        route_no_match.metadata = {"file": "src/api/items.py"}
        mock_discover.return_value = [route_match, route_no_match]

        mock_gen = MagicMock()
        mock_gen.generate.return_value = MagicMock(
            files={"test_users": MagicMock()},
            stats={"files": 1, "tests": 5},
            warnings=[],
        )
        mock_gen_cls.return_value = mock_gen

        result = generate_branch_tests(
            repo_path=MagicMock(),
            branch_name="feature/users",
            branch_id=3,
        )

        # Generator should have been called with only the matching route
        routes_arg = mock_gen_cls.call_args.kwargs["routes"]
        assert len(routes_arg) == 1
        assert routes_arg[0] is route_match
        assert result.files_generated == 1
        assert result.test_count == 5

    @patch(_PATCH_GENERATOR)
    @patch(_PATCH_DISCOVER)
    @patch(_PATCH_ANALYZER)
    def test_windows_backslash_paths_match(self, mock_analyzer_cls, mock_discover, mock_gen_cls):
        """Regression: Windows backslash metadata paths must match git forward-slash diff paths."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_diff(
            route_files=[FileChange(path="src/api/users.py", additions=10, status="modified")]
        )
        mock_analyzer_cls.return_value = mock_analyzer

        # Route metadata uses Windows backslashes
        route = MagicMock()
        route.metadata = {"file": "src\\api\\users.py"}
        mock_discover.return_value = [route]

        mock_gen = MagicMock()
        mock_gen.generate.return_value = MagicMock(
            files={"test_users": MagicMock()},
            stats={"files": 1, "tests": 3},
            warnings=[],
        )
        mock_gen_cls.return_value = mock_gen

        result = generate_branch_tests(
            repo_path=MagicMock(),
            branch_name="feature/win",
            branch_id=4,
        )

        # Despite backslash vs forward-slash, the route should match
        routes_arg = mock_gen_cls.call_args.kwargs["routes"]
        assert len(routes_arg) == 1
        assert result.files_generated == 1

    @patch(_PATCH_GENERATOR)
    @patch(_PATCH_DISCOVER)
    @patch(_PATCH_ANALYZER)
    def test_fallback_all_routes_when_no_metadata_match(self, mock_analyzer_cls, mock_discover, mock_gen_cls):
        """When no route metadata matches but route files changed, fall back to all routes."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_diff(
            route_files=[FileChange(path="src/api/users.py", additions=10, status="modified")]
        )
        mock_analyzer_cls.return_value = mock_analyzer

        # Route has no file metadata (e.g., OpenAPI-sourced)
        route = MagicMock()
        route.metadata = {}
        mock_discover.return_value = [route]

        mock_gen = MagicMock()
        mock_gen.generate.return_value = MagicMock(
            files={"test": MagicMock()},
            stats={"files": 1, "tests": 2},
            warnings=[],
        )
        mock_gen_cls.return_value = mock_gen

        result = generate_branch_tests(
            repo_path=MagicMock(),
            branch_name="feature/openapi",
            branch_id=5,
        )

        # Should fall back to all routes with a warning
        assert result.files_generated == 1
        assert any("Could not filter" in w for w in result.warnings)

    @patch(_PATCH_DISCOVER)
    @patch(_PATCH_ANALYZER)
    def test_no_routes_match_non_route_diff(self, mock_analyzer_cls, mock_discover):
        """When only non-route files changed and no routes match, return warning."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_diff(
            other_files=[FileChange(path="src/utils/helpers.py", additions=5, status="modified")]
        )
        mock_analyzer_cls.return_value = mock_analyzer

        route = MagicMock()
        route.metadata = {"file": "src/api/users.py"}
        mock_discover.return_value = [route]

        result = generate_branch_tests(
            repo_path=MagicMock(),
            branch_name="feature/utils",
            branch_id=6,
        )
        assert result.files_generated == 0
        assert any("No routes match" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# run_branch_tests() — mocked runner tests
# ---------------------------------------------------------------------------

_PATCH_PYTEST_RUNNER = "qaagent.runners.pytest_runner.PytestRunner"


class TestRunBranchTests:
    """Tests for run_branch_tests (mocked PytestRunner)."""

    def test_no_test_dir_raises(self, tmp_path):
        """Raises FileNotFoundError when no tests have been generated."""
        with patch("qaagent.branch.test_executor.BRANCH_TESTS_DIR", tmp_path):
            with pytest.raises(FileNotFoundError, match="No generated tests"):
                run_branch_tests(branch_id=999)

    def test_empty_dir_raises(self, tmp_path):
        """Raises FileNotFoundError when test dir exists but has no test files."""
        test_dir = tmp_path / "42"
        test_dir.mkdir()
        (test_dir / "conftest.py").write_text("# no tests", encoding="utf-8")

        with patch("qaagent.branch.test_executor.BRANCH_TESTS_DIR", tmp_path):
            with pytest.raises(FileNotFoundError, match="No generated tests"):
                run_branch_tests(branch_id=42)

    @patch(_PATCH_PYTEST_RUNNER)
    def test_success_returns_result(self, mock_runner_cls, tmp_path):
        """Successful run returns BranchRunResult with correct counts."""
        test_dir = tmp_path / "10"
        test_dir.mkdir()
        (test_dir / "test_users.py").write_text("def test_x(): pass", encoding="utf-8")

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(
            total=5, passed=4, failed=1, skipped=0,
        )
        mock_runner_cls.return_value = mock_runner

        with patch("qaagent.branch.test_executor.BRANCH_TESTS_DIR", tmp_path):
            result = run_branch_tests(branch_id=10)

        assert result.total == 5
        assert result.passed == 4
        assert result.failed == 1
        assert result.suite_type == "pytest"
        assert result.run_id.startswith("branch-10-")
