"""Tests for runner base models."""
from qaagent.runners.base import TestCase, TestResult, TestRunner
from qaagent.config.models import RunSettings


class TestTestCase:
    def test_default_values(self):
        tc = TestCase(name="test_example")
        assert tc.status == "passed"
        assert tc.duration == 0.0
        assert tc.output is None
        assert tc.error_message is None
        assert tc.route is None

    def test_failed_case(self):
        tc = TestCase(
            name="test_fail",
            status="failed",
            duration=1.5,
            error_message="assert False",
            output="traceback here",
        )
        assert tc.status == "failed"
        assert tc.duration == 1.5
        assert tc.error_message == "assert False"


class TestTestResult:
    def test_empty_result(self):
        r = TestResult(suite_name="unit", runner="pytest")
        assert r.total == 0
        assert r.success is True
        assert r.passed == 0

    def test_success_property(self):
        r = TestResult(suite_name="unit", runner="pytest", passed=5, failed=0, errors=0)
        assert r.success is True

    def test_failure_property(self):
        r = TestResult(suite_name="unit", runner="pytest", passed=3, failed=2, errors=0)
        assert r.success is False
        assert r.total == 5

    def test_error_property(self):
        r = TestResult(suite_name="unit", runner="pytest", passed=3, failed=0, errors=1)
        assert r.success is False

    def test_artifacts(self):
        r = TestResult(
            suite_name="unit",
            runner="pytest",
            artifacts={"junit": "/tmp/junit.xml"},
        )
        assert r.artifacts["junit"] == "/tmp/junit.xml"


class TestTestRunnerRouteMapping:
    """Test the _map_test_to_route method via a concrete subclass."""

    class _ConcreteRunner(TestRunner):
        runner_name = "test"
        def run(self, test_path, **kwargs):
            return TestResult(suite_name="test", runner="test")
        def parse_results(self, junit_path, stdout=""):
            return TestResult(suite_name="test", runner="test")

    def test_get_route(self):
        r = self._ConcreteRunner()
        assert r._map_test_to_route("test_get_pets_success") == "GET /pets"

    def test_post_route(self):
        r = self._ConcreteRunner()
        assert r._map_test_to_route("test_post_pets_success") == "POST /pets"

    def test_nested_route_with_param(self):
        r = self._ConcreteRunner()
        result = r._map_test_to_route("test_get_pets_pet_id_success")
        # pet_id detected as path param
        assert result == "GET /pets/{pet_id}"

    def test_delete_route_with_param(self):
        r = self._ConcreteRunner()
        result = r._map_test_to_route("test_delete_pets_pet_id_error")
        assert result == "DELETE /pets/{pet_id}"

    def test_route_without_param(self):
        r = self._ConcreteRunner()
        result = r._map_test_to_route("test_get_users_profile_success")
        assert result == "GET /users/profile"

    def test_no_method_returns_none(self):
        r = self._ConcreteRunner()
        assert r._map_test_to_route("test_something_random") is None


class TestRunSettings:
    def test_defaults(self):
        rs = RunSettings()
        assert rs.retry_count == 0
        assert rs.timeout == 300
        assert rs.suite_order == ["unit", "behave", "e2e"]
        assert rs.parallel is False
        assert rs.max_workers is None

    def test_custom(self):
        rs = RunSettings(
            retry_count=3,
            timeout=600,
            suite_order=["e2e", "unit"],
            parallel=True,
            max_workers=2,
        )
        assert rs.retry_count == 3
        assert rs.timeout == 600
        assert rs.suite_order == ["e2e", "unit"]
        assert rs.parallel is True
        assert rs.max_workers == 2
