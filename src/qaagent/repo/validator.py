"""
Repository structure validator.

Detects project type and validates structure:
- Next.js (App Router, Pages Router)
- FastAPI
- Flask
- Django
- Express
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class RepoValidator:
    """Validates repository structure and detects project type."""

    def __init__(self, repo_path: Path):
        """
        Initialize validator for a repository.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = Path(repo_path)

    def detect_project_type(self) -> Optional[str]:
        """
        Detect the project type from repository structure.

        Returns:
            Project type: "nextjs", "fastapi", "flask", "django", "express", or None
        """
        if self._is_nextjs():
            return "nextjs"
        if self._is_fastapi():
            return "fastapi"
        if self._is_flask():
            return "flask"
        if self._is_django():
            return "django"
        if self._is_express():
            return "express"
        return None

    def validate(self) -> dict:
        """
        Validate repository structure.

        Returns:
            Dict with: valid, project_type, issues, api_routes_found
        """
        project_type = self.detect_project_type()

        issues = []
        api_routes_found = False

        if project_type == "nextjs":
            api_routes_found = self._has_nextjs_routes()
            if not api_routes_found:
                issues.append("No API routes found in src/app/api/ or app/api/")

        elif project_type == "fastapi":
            api_routes_found = self._has_fastapi_routes()
            if not api_routes_found:
                issues.append("No FastAPI routes found (no main.py or app.py with FastAPI())")

        elif project_type is None:
            issues.append("Unknown project type - no framework detected")

        return {
            "valid": len(issues) == 0,
            "project_type": project_type,
            "issues": issues,
            "api_routes_found": api_routes_found,
        }

    def _is_nextjs(self) -> bool:
        """Check if repository is a Next.js project."""
        # Check for next.config files
        if (self.repo_path / "next.config.js").exists():
            return True
        if (self.repo_path / "next.config.mjs").exists():
            return True
        if (self.repo_path / "next.config.ts").exists():
            return True

        # Check package.json for Next.js dependency
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                import json

                pkg = json.loads(package_json.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    return True
            except Exception:
                pass

        return False

    def _is_fastapi(self) -> bool:
        """Check if repository is a FastAPI project."""
        # Check for common FastAPI files
        for filename in ["main.py", "app.py", "api.py"]:
            file_path = self.repo_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text()
                    if "fastapi" in content.lower() or "FastAPI" in content:
                        return True
                except Exception:
                    pass

        # Check requirements.txt or pyproject.toml
        if (self.repo_path / "requirements.txt").exists():
            try:
                reqs = (self.repo_path / "requirements.txt").read_text()
                if "fastapi" in reqs.lower():
                    return True
            except Exception:
                pass

        if (self.repo_path / "pyproject.toml").exists():
            try:
                toml_content = (self.repo_path / "pyproject.toml").read_text()
                if "fastapi" in toml_content.lower():
                    return True
            except Exception:
                pass

        return False

    def _is_flask(self) -> bool:
        """Check if repository is a Flask project."""
        # Check for Flask in common files
        for filename in ["app.py", "main.py", "application.py"]:
            file_path = self.repo_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text()
                    if "flask" in content.lower() or "Flask" in content:
                        return True
                except Exception:
                    pass

        # Check dependencies
        if (self.repo_path / "requirements.txt").exists():
            try:
                reqs = (self.repo_path / "requirements.txt").read_text()
                if "flask" in reqs.lower():
                    return True
            except Exception:
                pass

        return False

    def _is_django(self) -> bool:
        """Check if repository is a Django project."""
        # Check for manage.py
        if (self.repo_path / "manage.py").exists():
            return True

        # Check for Django in requirements
        if (self.repo_path / "requirements.txt").exists():
            try:
                reqs = (self.repo_path / "requirements.txt").read_text()
                if "django" in reqs.lower():
                    return True
            except Exception:
                pass

        return False

    def _is_express(self) -> bool:
        """Check if repository is an Express.js project."""
        # Check package.json for Express
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                import json

                pkg = json.loads(package_json.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "express" in deps:
                    return True
            except Exception:
                pass

        return False

    def _has_nextjs_routes(self) -> bool:
        """Check if Next.js project has API routes."""
        # Check src/app/api
        src_api = self.repo_path / "src" / "app" / "api"
        if src_api.exists():
            route_files = list(src_api.rglob("route.ts")) + list(src_api.rglob("route.js"))
            if route_files:
                return True

        # Check app/api
        app_api = self.repo_path / "app" / "api"
        if app_api.exists():
            route_files = list(app_api.rglob("route.ts")) + list(app_api.rglob("route.js"))
            if route_files:
                return True

        return False

    def _has_fastapi_routes(self) -> bool:
        """Check if FastAPI project has route definitions."""
        # Look for @app.get, @app.post, etc. in Python files
        for py_file in self.repo_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                if "@app." in content or "@router." in content:
                    return True
            except Exception:
                pass

        return False

    def get_framework_parser(self):
        """Return a FrameworkParser instance for the detected project type, or None."""
        from qaagent.discovery import get_framework_parser

        project_type = self.detect_project_type()
        if project_type:
            return get_framework_parser(project_type)
        return None

    def get_api_directory(self) -> Optional[Path]:
        """
        Get the main API directory for the detected project type.

        Returns:
            Path to API directory or None
        """
        project_type = self.detect_project_type()

        if project_type == "nextjs":
            # Check src/app/api first
            src_api = self.repo_path / "src" / "app" / "api"
            if src_api.exists():
                return src_api

            # Check app/api
            app_api = self.repo_path / "app" / "api"
            if app_api.exists():
                return app_api

        elif project_type in ("fastapi", "flask", "django"):
            # Return repository root for Python projects
            return self.repo_path

        return None
