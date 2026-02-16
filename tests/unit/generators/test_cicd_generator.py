"""Tests for CI/CD pipeline generator."""
from pathlib import Path

import pytest
import yaml

from qaagent.generators.cicd_generator import CICDGenerator, SuiteFlags


class TestCICDGenerator:
    def test_generate_github_actions(self, tmp_path):
        gen = CICDGenerator(framework="fastapi", project_name="test-app")
        dest = gen.generate("github", tmp_path)

        assert dest.exists()
        assert dest.name == "qa-pipeline.yml"
        assert ".github/workflows" in dest.as_posix()
        content = dest.read_text()
        assert "QA Pipeline" in content

    def test_generate_gitlab_ci(self, tmp_path):
        gen = CICDGenerator(framework="flask", project_name="my-flask")
        dest = gen.generate("gitlab", tmp_path)

        assert dest.exists()
        assert dest.name == ".gitlab-ci.yml"
        content = dest.read_text()
        assert "stages:" in content

    def test_invalid_platform(self, tmp_path):
        gen = CICDGenerator()
        with pytest.raises(ValueError, match="Unsupported platform"):
            gen.generate("jenkins", tmp_path)

    def test_github_includes_bootstrap(self, tmp_path):
        gen = CICDGenerator(framework="fastapi", project_name="myapp")
        dest = gen.generate("github", tmp_path)
        content = dest.read_text()

        assert "qaagent config init" in content
        assert "qaagent use myapp" in content

    def test_gitlab_includes_bootstrap(self, tmp_path):
        gen = CICDGenerator(framework="django", project_name="djapp")
        dest = gen.generate("gitlab", tmp_path)
        content = dest.read_text()

        assert "qaagent config init" in content
        assert "qaagent use djapp" in content

    def test_github_framework_in_template(self, tmp_path):
        gen = CICDGenerator(framework="django", project_name="djapp")
        dest = gen.generate("github", tmp_path)
        content = dest.read_text()

        assert "django" in content

    def test_github_suites_unit_only(self, tmp_path):
        gen = CICDGenerator(suites=SuiteFlags(unit=True, behave=False, e2e=False))
        dest = gen.generate("github", tmp_path)
        content = dest.read_text()

        assert "unit tests" in content.lower() or "pytest" in content
        assert "behave" not in content.lower() or "BDD" not in content
        assert "playwright" not in content.lower()

    def test_github_suites_all(self, tmp_path):
        gen = CICDGenerator(suites=SuiteFlags(unit=True, behave=True, e2e=True))
        dest = gen.generate("github", tmp_path)
        content = dest.read_text()

        assert "pytest" in content
        assert "behave" in content
        assert "playwright" in content.lower()

    def test_gitlab_suites_all(self, tmp_path):
        gen = CICDGenerator(suites=SuiteFlags(unit=True, behave=True, e2e=True))
        dest = gen.generate("gitlab", tmp_path)
        content = dest.read_text()

        assert "run-unit-tests" in content
        assert "run-behave-tests" in content
        assert "run-e2e-tests" in content

    def test_github_base_url_from_secrets(self, tmp_path):
        gen = CICDGenerator()
        dest = gen.generate("github", tmp_path)
        content = dest.read_text()

        assert "secrets.BASE_URL" in content

    def test_gitlab_base_url_from_variables(self, tmp_path):
        gen = CICDGenerator()
        dest = gen.generate("gitlab", tmp_path)
        content = dest.read_text()

        assert "BASE_URL" in content

    def test_python_version(self, tmp_path):
        gen = CICDGenerator(python_version="3.12")
        dest = gen.generate("github", tmp_path)
        content = dest.read_text()

        assert "3.12" in content

    def test_api_token(self, tmp_path):
        gen = CICDGenerator(api_token=True)
        dest = gen.generate("github", tmp_path)
        content = dest.read_text()

        assert "API_TOKEN" in content

    def test_github_yaml_is_valid(self, tmp_path):
        """Generated GitHub Actions YAML should be parseable."""
        gen = CICDGenerator(
            framework="fastapi",
            project_name="test",
            suites=SuiteFlags(unit=True, behave=True, e2e=True),
        )
        dest = gen.generate("github", tmp_path)
        content = dest.read_text()

        # Should be valid YAML
        parsed = yaml.safe_load(content)
        assert parsed is not None
        assert "jobs" in parsed

    def test_gitlab_yaml_is_valid(self, tmp_path):
        """Generated GitLab CI YAML should be parseable."""
        gen = CICDGenerator(
            framework="flask",
            project_name="test",
            suites=SuiteFlags(unit=True, behave=True, e2e=True),
        )
        dest = gen.generate("gitlab", tmp_path)
        content = dest.read_text()

        parsed = yaml.safe_load(content)
        assert parsed is not None
        assert "stages" in parsed

    def test_ci_renders_for_each_framework(self, tmp_path):
        """Templates should render without errors for each supported framework."""
        for fw in ("fastapi", "flask", "django", "nextjs"):
            gen = CICDGenerator(framework=fw, project_name=f"test-{fw}")
            dest = gen.generate("github", tmp_path / fw)
            assert dest.exists()
            content = dest.read_text()
            assert fw in content
