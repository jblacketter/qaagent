"""Tests for repo/validator.py — RepoValidator project detection."""
from __future__ import annotations

import json
from pathlib import Path

from qaagent.repo.validator import RepoValidator


class TestDetectProjectType:
    def test_nextjs_from_config(self, tmp_path):
        (tmp_path / "next.config.js").write_text("module.exports = {}")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "nextjs"

    def test_nextjs_from_config_mjs(self, tmp_path):
        (tmp_path / "next.config.mjs").write_text("export default {}")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "nextjs"

    def test_nextjs_from_package_json(self, tmp_path):
        pkg = {"dependencies": {"next": "14.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "nextjs"

    def test_fastapi_from_main_py(self, tmp_path):
        (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "fastapi"

    def test_fastapi_from_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn\n")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "fastapi"

    def test_fastapi_from_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi"]\n')
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "fastapi"

    def test_flask_from_app_py(self, tmp_path):
        (tmp_path / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "flask"

    def test_flask_from_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==3.0.0\n")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "flask"

    def test_django_from_manage_py(self, tmp_path):
        (tmp_path / "manage.py").write_text("#!/usr/bin/env python\nimport django\n")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "django"

    def test_django_from_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("django==5.0\n")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "django"

    def test_express_from_package_json(self, tmp_path):
        pkg = {"dependencies": {"express": "4.18.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "express"

    def test_none_for_empty_repo(self, tmp_path):
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() is None

    def test_go_from_go_mod(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/app\nrequire github.com/gin-gonic/gin v1.9.0\n")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "go"

    def test_ruby_from_gemfile(self, tmp_path):
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"\ngem "rails"\n')
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "ruby"

    def test_rust_from_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[dependencies]\naxum = \"0.7\"\n")
        v = RepoValidator(tmp_path)
        assert v.detect_project_type() == "rust"


class TestValidate:
    def test_valid_nextjs_with_routes(self, tmp_path):
        (tmp_path / "next.config.js").write_text("module.exports = {}")
        api_dir = tmp_path / "src" / "app" / "api" / "users"
        api_dir.mkdir(parents=True)
        (api_dir / "route.ts").write_text("export async function GET() {}")

        result = RepoValidator(tmp_path).validate()

        assert result["valid"] is True
        assert result["project_type"] == "nextjs"
        assert result["api_routes_found"] is True

    def test_nextjs_without_routes(self, tmp_path):
        (tmp_path / "next.config.js").write_text("module.exports = {}")

        result = RepoValidator(tmp_path).validate()

        assert result["valid"] is False
        assert "No API routes" in result["issues"][0]

    def test_valid_fastapi_with_routes(self, tmp_path):
        (tmp_path / "main.py").write_text(
            "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/items')\ndef items(): ...\n"
        )

        result = RepoValidator(tmp_path).validate()

        assert result["valid"] is True
        assert result["project_type"] == "fastapi"
        assert result["api_routes_found"] is True

    def test_fastapi_without_routes(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        result = RepoValidator(tmp_path).validate()

        assert result["valid"] is False
        assert result["project_type"] == "fastapi"

    def test_unknown_project(self, tmp_path):
        result = RepoValidator(tmp_path).validate()

        assert result["valid"] is False
        assert result["project_type"] is None
        assert "Unknown project type" in result["issues"][0]

    def test_valid_go_with_routes(self, tmp_path):
        (tmp_path / "go.mod").write_text("module x\nrequire github.com/gin-gonic/gin v1.9.0\n")
        (tmp_path / "main.go").write_text('package main\nfunc main(){ r := gin.Default(); r.GET("/health", h) }')

        result = RepoValidator(tmp_path).validate()

        assert result["valid"] is True
        assert result["project_type"] == "go"
        assert result["api_routes_found"] is True

    def test_valid_ruby_with_routes(self, tmp_path):
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"\ngem "sinatra"\n')
        (tmp_path / "app.rb").write_text('get "/health" do\n "ok"\nend\n')

        result = RepoValidator(tmp_path).validate()

        assert result["valid"] is True
        assert result["project_type"] == "ruby"
        assert result["api_routes_found"] is True

    def test_valid_rust_with_routes(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[dependencies]\nactix-web = \"4\"\n")
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.rs").write_text('#[get("/health")]\nasync fn health() {}')

        result = RepoValidator(tmp_path).validate()

        assert result["valid"] is True
        assert result["project_type"] == "rust"
        assert result["api_routes_found"] is True


class TestGetApiDirectory:
    def test_nextjs_src_app_api(self, tmp_path):
        (tmp_path / "next.config.js").write_text("")
        api_dir = tmp_path / "src" / "app" / "api"
        api_dir.mkdir(parents=True)

        v = RepoValidator(tmp_path)
        assert v.get_api_directory() == api_dir

    def test_nextjs_app_api(self, tmp_path):
        (tmp_path / "next.config.js").write_text("")
        api_dir = tmp_path / "app" / "api"
        api_dir.mkdir(parents=True)

        v = RepoValidator(tmp_path)
        assert v.get_api_directory() == api_dir

    def test_fastapi_returns_root(self, tmp_path):
        (tmp_path / "main.py").write_text("from fastapi import FastAPI\n")

        v = RepoValidator(tmp_path)
        assert v.get_api_directory() == tmp_path

    def test_unknown_returns_none(self, tmp_path):
        v = RepoValidator(tmp_path)
        assert v.get_api_directory() is None

    def test_go_returns_root(self, tmp_path):
        (tmp_path / "go.mod").write_text("module x\nrequire github.com/gin-gonic/gin v1.9.0\n")

        v = RepoValidator(tmp_path)
        assert v.get_api_directory() == tmp_path

    def test_ruby_returns_root(self, tmp_path):
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"\ngem "rails"\n')

        v = RepoValidator(tmp_path)
        assert v.get_api_directory() == tmp_path

    def test_rust_returns_root(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[dependencies]\naxum = \"0.7\"\n")

        v = RepoValidator(tmp_path)
        assert v.get_api_directory() == tmp_path
