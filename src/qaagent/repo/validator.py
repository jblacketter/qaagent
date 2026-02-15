"""
Repository structure validator.

Detects project type and validates structure:
- Next.js (App Router, Pages Router)
- FastAPI
- Flask
- Django
- Go (net/http, Gin, Echo)
- Ruby (Rails, Sinatra)
- Rust (Actix Web, Axum)
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
            Project type: "nextjs", "fastapi", "flask", "django", "go", "ruby", "rust", "express", or None
        """
        if self._is_nextjs():
            return "nextjs"
        if self._is_fastapi():
            return "fastapi"
        if self._is_flask():
            return "flask"
        if self._is_django():
            return "django"
        if self._is_go():
            return "go"
        if self._is_ruby():
            return "ruby"
        if self._is_rust():
            return "rust"
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

        elif project_type == "go":
            api_routes_found = self._has_go_routes()
            if not api_routes_found:
                issues.append("No Go HTTP routes found (net/http, Gin, or Echo patterns)")

        elif project_type == "ruby":
            api_routes_found = self._has_ruby_routes()
            if not api_routes_found:
                issues.append("No Ruby routes found (Rails routes.rb or Sinatra handlers)")

        elif project_type == "rust":
            api_routes_found = self._has_rust_routes()
            if not api_routes_found:
                issues.append("No Rust routes found (Actix or Axum route patterns)")

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

    def _is_go(self) -> bool:
        """Check if repository is a Go web service project."""
        go_mod = self.repo_path / "go.mod"
        if go_mod.exists():
            try:
                mod = go_mod.read_text(encoding="utf-8").lower()
                if any(dep in mod for dep in ("gin-gonic/gin", "labstack/echo", "gorilla/mux", "go-chi/chi")):
                    return True
            except Exception:
                pass
        return self._has_go_routes()

    def _is_ruby(self) -> bool:
        """Check if repository is a Ruby web project."""
        if (self.repo_path / "config" / "routes.rb").exists():
            return True

        gemfile = self.repo_path / "Gemfile"
        if gemfile.exists():
            try:
                gems = gemfile.read_text(encoding="utf-8").lower()
                if "rails" in gems or "sinatra" in gems:
                    return True
            except Exception:
                pass

        for rb_file in self.repo_path.rglob("*.rb"):
            rel = str(rb_file.relative_to(self.repo_path))
            if any(skip in rel for skip in ("vendor/", "spec/", "test/", ".bundle/")):
                continue
            try:
                content = rb_file.read_text(encoding="utf-8").lower()
            except Exception:
                continue
            if "sinatra::base" in content or "require 'sinatra'" in content or 'require "sinatra"' in content:
                return True

        return False

    def _is_rust(self) -> bool:
        """Check if repository is a Rust web project."""
        cargo = self.repo_path / "Cargo.toml"
        if cargo.exists():
            try:
                cargo_text = cargo.read_text(encoding="utf-8").lower()
                if "actix-web" in cargo_text or "axum" in cargo_text:
                    return True
            except Exception:
                pass
        return self._has_rust_routes()

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

    def _has_go_routes(self) -> bool:
        """Check if Go project has HTTP route definitions."""
        patterns = (
            "http.HandleFunc(",
            "http.Handle(",
            ".GET(",
            ".POST(",
            ".PUT(",
            ".PATCH(",
            ".DELETE(",
            ".Group(",
            "gin.Default(",
            "gin.New(",
            "echo.New(",
        )
        for go_file in self.repo_path.rglob("*.go"):
            rel = str(go_file.relative_to(self.repo_path))
            if any(skip in rel for skip in ("vendor/", "testdata/", "__pycache__/")):
                continue
            if go_file.name.endswith("_test.go"):
                continue
            try:
                content = go_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if any(pattern in content for pattern in patterns):
                return True
        return False

    def _has_ruby_routes(self) -> bool:
        """Check if Ruby project has Rails/Sinatra route definitions."""
        routes_rb = self.repo_path / "config" / "routes.rb"
        if routes_rb.exists():
            try:
                content = routes_rb.read_text(encoding="utf-8")
            except Exception:
                content = ""
            if any(token in content for token in ("routes.draw", "resources :", "resource :", "get ", "post ", "match ")):
                return True

        route_re = ("get ", "post ", "put ", "patch ", "delete ", "head ", "options ")
        for rb_file in self.repo_path.rglob("*.rb"):
            rel = str(rb_file.relative_to(self.repo_path))
            if any(skip in rel for skip in ("vendor/", "spec/", "test/", ".bundle/")):
                continue
            try:
                content = rb_file.read_text(encoding="utf-8").lower()
            except Exception:
                continue
            if any(method in content for method in route_re):
                return True
        return False

    def _has_rust_routes(self) -> bool:
        """Check if Rust project has Actix/Axum route definitions."""
        patterns = (
            "#[get(",
            "#[post(",
            "#[put(",
            "#[patch(",
            "#[delete(",
            ".route(",
            "web::get()",
            "web::post()",
            "router::new()",
            "axum::routing::",
        )
        for rs_file in self.repo_path.rglob("*.rs"):
            rel = str(rs_file.relative_to(self.repo_path))
            if any(skip in rel for skip in ("target/", "tests/", "benches/")):
                continue
            try:
                content = rs_file.read_text(encoding="utf-8").lower()
            except Exception:
                continue
            if any(pattern.lower() in content for pattern in patterns):
                return True
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

        elif project_type in ("fastapi", "flask", "django", "go", "ruby", "rust"):
            # Return repository root for server projects discovered from source.
            return self.repo_path

        return None
