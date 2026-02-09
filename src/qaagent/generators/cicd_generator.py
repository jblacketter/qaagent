"""CI/CD pipeline template generator."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel


class SuiteFlags(BaseModel):
    """Which test suites are enabled."""
    unit: bool = True
    behave: bool = False
    e2e: bool = False


class CICDGenerator:
    """Generate CI/CD pipeline YAML from Jinja2 templates."""

    TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "cicd"

    def __init__(
        self,
        framework: str = "fastapi",
        project_name: str = "my-project",
        python_version: str = "3.11",
        suites: Optional[SuiteFlags] = None,
        api_token: bool = False,
    ) -> None:
        self.framework = framework
        self.project_name = project_name
        self.python_version = python_version
        self.suites = suites or SuiteFlags()
        self.api_token = api_token

        self._env = Environment(
            loader=FileSystemLoader(str(self.TEMPLATES_DIR)),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _context(self) -> Dict:
        return {
            "framework": self.framework,
            "project_name": self.project_name,
            "python_version": self.python_version,
            "suites": self.suites,
            "api_token": self.api_token,
        }

    def generate_github_actions(self, output_dir: Path) -> Path:
        """Generate a GitHub Actions workflow YAML.

        Returns the path to the generated file.
        """
        template = self._env.get_template("github_actions.yml.j2")
        content = template.render(**self._context())

        dest_dir = output_dir / ".github" / "workflows"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "qa-pipeline.yml"
        dest.write_text(content, encoding="utf-8")
        return dest

    def generate_gitlab_ci(self, output_dir: Path) -> Path:
        """Generate a GitLab CI YAML.

        Returns the path to the generated file.
        """
        template = self._env.get_template("gitlab_ci.yml.j2")
        content = template.render(**self._context())

        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / ".gitlab-ci.yml"
        dest.write_text(content, encoding="utf-8")
        return dest

    def generate(self, platform: str, output_dir: Path) -> Path:
        """Generate a pipeline for the specified platform.

        Args:
            platform: "github" or "gitlab"
            output_dir: Project root to write into

        Returns:
            Path to the generated file.
        """
        if platform == "github":
            return self.generate_github_actions(output_dir)
        elif platform == "gitlab":
            return self.generate_gitlab_ci(output_dir)
        else:
            raise ValueError(f"Unsupported platform: {platform}. Use 'github' or 'gitlab'.")
