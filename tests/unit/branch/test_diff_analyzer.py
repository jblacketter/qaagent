"""Tests for branch diff file categorization."""

from qaagent.branch.diff_analyzer import _categorize_file


class TestCategorizeFile:
    """Tests for _categorize_file() path-pattern heuristic."""

    # --- Route files ---

    def test_route_directory(self):
        assert _categorize_file("src/routes/users.py") == "route"

    def test_views_directory(self):
        assert _categorize_file("app/views/login.py") == "route"

    def test_api_directory(self):
        assert _categorize_file("src/api/endpoints.py") == "route"

    def test_controllers_directory(self):
        assert _categorize_file("src/controllers/auth.py") == "route"

    def test_handlers_directory(self):
        assert _categorize_file("src/handlers/webhook.py") == "route"

    def test_route_suffix(self):
        assert _categorize_file("src/user_routes.py") == "route"

    def test_views_suffix(self):
        assert _categorize_file("src/auth_views.py") == "route"

    def test_api_suffix(self):
        assert _categorize_file("src/items_api.py") == "route"

    # --- Test files ---

    def test_test_prefix(self):
        assert _categorize_file("test_main.py") == "test"

    def test_tests_directory(self):
        assert _categorize_file("tests/unit/test_foo.py") == "test"

    def test_spec_directory(self):
        assert _categorize_file("spec/models/user_spec.rb") == "test"

    def test_dunder_tests_directory(self):
        assert _categorize_file("src/__tests__/App.test.js") == "test"

    def test_dot_test_extension(self):
        assert _categorize_file("src/utils.test.ts") == "test"

    def test_dot_spec_extension(self):
        assert _categorize_file("src/utils.spec.ts") == "test"

    # --- Config files ---

    def test_yaml_extension(self):
        assert _categorize_file("config.yaml") == "config"

    def test_yml_extension(self):
        assert _categorize_file("docker-compose.yml") == "config"

    def test_toml_extension(self):
        assert _categorize_file("pyproject.toml") == "config"

    def test_ini_extension(self):
        assert _categorize_file("setup.ini") == "config"

    def test_env_file(self):
        assert _categorize_file(".env") == "config"

    def test_config_directory(self):
        assert _categorize_file("config/database.py") == "config"

    def test_settings_directory(self):
        assert _categorize_file("settings/production.py") == "config"

    def test_dockerfile(self):
        assert _categorize_file("Dockerfile") == "config"

    def test_dockerfile_lowercase(self):
        assert _categorize_file("dockerfile") == "config"

    def test_dockerfile_nested(self):
        assert _categorize_file("deploy/Dockerfile.prod") == "config"

    def test_docker_compose(self):
        assert _categorize_file("docker-compose.yml") == "config"

    def test_github_workflow(self):
        assert _categorize_file(".github/workflows/ci.yml") == "config"

    def test_gitlab_ci(self):
        assert _categorize_file(".gitlab-ci.yml") == "config"

    def test_makefile(self):
        assert _categorize_file("Makefile") == "config"

    def test_makefile_lowercase(self):
        assert _categorize_file("makefile") == "config"

    # --- Migration files ---

    def test_migration_directory(self):
        assert _categorize_file("migrations/0001_initial.py") == "migration"

    def test_alembic_directory(self):
        assert _categorize_file("alembic/versions/abc123.py") == "migration"

    def test_migration_in_path(self):
        assert _categorize_file("db/migration_script.py") == "migration"

    # --- Other files ---

    def test_plain_python_file(self):
        assert _categorize_file("src/models/user.py") == "other"

    def test_readme(self):
        assert _categorize_file("README.md") == "other"

    def test_plain_js_file(self):
        assert _categorize_file("src/utils/helpers.js") == "other"

    # --- Priority: migration beats others ---

    def test_migration_in_test_dir(self):
        """Migration pattern takes precedence over test pattern."""
        assert _categorize_file("tests/migrations/test_migration.py") == "migration"
