"""Tests for branch checklist generation."""

from qaagent.branch.checklist_generator import generate_checklist, _is_ci_config
from qaagent.branch.diff_analyzer import DiffResult, FileChange


# ---------------------------------------------------------------------------
# Helper to build a DiffResult with pre-categorized files
# ---------------------------------------------------------------------------

def _make_diff(
    route_files: list[FileChange] | None = None,
    test_files: list[FileChange] | None = None,
    config_files: list[FileChange] | None = None,
    migration_files: list[FileChange] | None = None,
    other_files: list[FileChange] | None = None,
) -> DiffResult:
    all_files = []
    for group in (route_files, test_files, config_files, migration_files, other_files):
        if group:
            all_files.extend(group)

    return DiffResult(
        branch_name="feature/test",
        base_branch="main",
        files=all_files,
        diff_hash="abc123",
        route_files=route_files or [],
        test_files=test_files or [],
        config_files=config_files or [],
        migration_files=migration_files or [],
        other_files=other_files or [],
    )


# ---------------------------------------------------------------------------
# _is_ci_config tests — case-sensitivity regression
# ---------------------------------------------------------------------------

class TestIsCiConfig:
    """Verify _is_ci_config handles case correctly (all comparisons are lowered)."""

    def test_dockerfile_uppercase(self):
        assert _is_ci_config("Dockerfile") is True

    def test_dockerfile_lowercase(self):
        assert _is_ci_config("dockerfile") is True

    def test_makefile_uppercase(self):
        assert _is_ci_config("Makefile") is True

    def test_makefile_lowercase(self):
        assert _is_ci_config("makefile") is True

    def test_jenkinsfile_uppercase(self):
        assert _is_ci_config("Jenkinsfile") is True

    def test_jenkinsfile_lowercase(self):
        assert _is_ci_config("jenkinsfile") is True

    def test_github_workflow(self):
        assert _is_ci_config(".github/workflows/ci.yml") is True

    def test_gitlab_ci(self):
        assert _is_ci_config(".gitlab-ci.yml") is True

    def test_docker_compose(self):
        assert _is_ci_config("docker-compose.yml") is True

    def test_regular_yaml_is_not_ci(self):
        assert _is_ci_config("config.yaml") is False

    def test_regular_python_is_not_ci(self):
        assert _is_ci_config("src/main.py") is False


# ---------------------------------------------------------------------------
# Checklist generation tests
# ---------------------------------------------------------------------------

class TestGenerateChecklist:
    """Tests for generate_checklist() — categories, priorities, edge cases."""

    def test_empty_diff_gives_fallback_item(self):
        diff = _make_diff()
        checklist = generate_checklist(diff, branch_id=1)
        assert len(checklist.items) == 1
        assert checklist.items[0].category == "regression"
        assert checklist.items[0].priority == "low"

    def test_route_added_generates_high_priority_items(self):
        diff = _make_diff(route_files=[
            FileChange(path="src/routes/users.py", additions=50, deletions=0, status="added"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        route_items = [i for i in checklist.items if i.category == "route_change"]
        assert len(route_items) == 3  # valid inputs, edge-case inputs, auth
        assert all(i.priority == "high" for i in route_items)

    def test_route_modified_generates_items(self):
        diff = _make_diff(route_files=[
            FileChange(path="src/routes/users.py", additions=10, deletions=5, status="modified"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        route_items = [i for i in checklist.items if i.category == "route_change"]
        assert len(route_items) == 2  # expected responses, edge-case inputs

    def test_route_deleted_generates_client_check(self):
        diff = _make_diff(route_files=[
            FileChange(path="src/routes/old.py", additions=0, deletions=30, status="deleted"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        route_items = [i for i in checklist.items if i.category == "route_change"]
        assert len(route_items) == 1
        assert "no longer referenced" in route_items[0].description

    def test_route_changes_add_integration_test_summary(self):
        diff = _make_diff(route_files=[
            FileChange(path="src/routes/users.py", additions=10, deletions=5, status="modified"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        regression_items = [i for i in checklist.items if i.category == "regression"]
        assert any("integration test suite" in i.description for i in regression_items)

    def test_migration_generates_high_priority_data_integrity(self):
        diff = _make_diff(migration_files=[
            FileChange(path="alembic/versions/001.py", additions=20, deletions=0, status="added"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        data_items = [i for i in checklist.items if i.category == "data_integrity"]
        assert len(data_items) == 2  # applies cleanly, data integrity
        assert all(i.priority == "high" for i in data_items)

    def test_config_change_generates_medium_priority(self):
        diff = _make_diff(config_files=[
            FileChange(path="config.yaml", additions=5, deletions=2, status="modified"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        config_items = [i for i in checklist.items if i.category == "config"]
        assert len(config_items) == 1
        assert config_items[0].priority == "medium"

    def test_ci_config_adds_extra_high_priority_item(self):
        diff = _make_diff(config_files=[
            FileChange(path="Dockerfile", additions=10, deletions=3, status="modified"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        config_items = [i for i in checklist.items if i.category == "config"]
        assert len(config_items) == 2  # general config + CI/CD pipeline
        assert any(i.priority == "high" for i in config_items)
        assert any("CI/CD" in i.description for i in config_items)

    def test_makefile_classified_as_ci_config(self):
        """Regression: Makefile must be recognized as CI config (case-insensitive)."""
        diff = _make_diff(config_files=[
            FileChange(path="Makefile", additions=5, deletions=1, status="modified"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        config_items = [i for i in checklist.items if i.category == "config"]
        assert any("CI/CD" in i.description for i in config_items)

    def test_added_test_file_generates_regression_item(self):
        diff = _make_diff(test_files=[
            FileChange(path="tests/test_new.py", additions=40, deletions=0, status="added"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        regression_items = [i for i in checklist.items if i.category == "regression"]
        assert len(regression_items) == 1
        assert "new test file" in regression_items[0].description.lower()

    def test_deleted_test_file_is_high_priority(self):
        diff = _make_diff(test_files=[
            FileChange(path="tests/test_old.py", additions=0, deletions=50, status="deleted"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        regression_items = [i for i in checklist.items if i.category == "regression"]
        assert len(regression_items) == 1
        assert regression_items[0].priority == "high"

    def test_new_other_file_generates_coverage_item(self):
        diff = _make_diff(other_files=[
            FileChange(path="src/utils/helpers.py", additions=30, deletions=0, status="added"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        new_items = [i for i in checklist.items if i.category == "new_code"]
        assert len(new_items) == 1
        assert "coverage" in new_items[0].description.lower()

    def test_large_diff_generates_edge_case_item(self):
        diff = _make_diff(other_files=[
            FileChange(path="src/big_refactor.py", additions=80, deletions=50, status="modified"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        edge_items = [i for i in checklist.items if i.category == "edge_case"]
        assert len(edge_items) == 1
        assert "130" not in edge_items[0].description  # Should show 80+/50-
        assert "80" in edge_items[0].description

    def test_small_diff_no_edge_case(self):
        diff = _make_diff(other_files=[
            FileChange(path="src/small.py", additions=5, deletions=3, status="modified"),
        ])
        checklist = generate_checklist(diff, branch_id=1)
        edge_items = [i for i in checklist.items if i.category == "edge_case"]
        assert len(edge_items) == 0

    def test_checklist_metadata(self):
        diff = _make_diff()
        checklist = generate_checklist(diff, branch_id=42)
        assert checklist.branch_id == 42
        assert checklist.format == "checklist"
        assert checklist.source_diff_hash == "abc123"

    def test_mixed_diff_all_categories(self):
        """Full scenario: diff with route, migration, config, test, and other files."""
        diff = _make_diff(
            route_files=[
                FileChange(path="src/api/users.py", additions=20, deletions=5, status="modified"),
            ],
            migration_files=[
                FileChange(path="migrations/002.py", additions=15, deletions=0, status="added"),
            ],
            config_files=[
                FileChange(path=".github/workflows/ci.yml", additions=3, deletions=1, status="modified"),
            ],
            test_files=[
                FileChange(path="tests/test_users.py", additions=30, deletions=0, status="added"),
            ],
            other_files=[
                FileChange(path="src/models/user.py", additions=10, deletions=2, status="added"),
            ],
        )
        checklist = generate_checklist(diff, branch_id=1)
        categories = {item.category for item in checklist.items}
        assert "route_change" in categories
        assert "data_integrity" in categories
        assert "config" in categories
        assert "regression" in categories
        assert "new_code" in categories
