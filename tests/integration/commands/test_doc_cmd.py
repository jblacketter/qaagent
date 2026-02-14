"""Integration tests for doc CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from qaagent.commands import app
from qaagent.doc.models import (
    AppDocumentation,
    FeatureArea,
    Integration,
    IntegrationType,
    RouteDoc,
)

runner = CliRunner()

# Lazy local imports in doc_cmd.py mean we must patch at the source module,
# not at qaagent.commands.doc_cmd.
_PATCH_LOAD_PROFILE = "qaagent.config.load_active_profile"
_PATCH_DISCOVER_ROUTES = "qaagent.doc.generator.discover_routes"
_PATCH_LOAD_DOC = "qaagent.doc.generator.load_documentation"


def _mock_active_profile(name="testapp", path=None):
    entry = MagicMock()
    entry.name = name
    entry.resolved_path.return_value = Path(path) if path else Path("/tmp/testapp")
    profile = MagicMock()
    profile.project.name = name
    return entry, profile


def _sample_doc():
    return AppDocumentation(
        app_name="Test App",
        summary="A test application.",
        total_routes=3,
        content_hash="abc123",
        features=[
            FeatureArea(
                id="users",
                name="Users",
                routes=[RouteDoc(path="/users", method="GET", summary="List users")],
                crud_operations=["read"],
                auth_required=True,
            ),
        ],
        integrations=[
            Integration(id="redis", name="Redis", type=IntegrationType.DATABASE),
        ],
    )


class TestDocGenerate:
    def test_generate_basic(self, tmp_path):
        entry, profile = _mock_active_profile(path=str(tmp_path))

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_DISCOVER_ROUTES, return_value=[]):
            result = runner.invoke(app, ["doc", "generate", "--no-llm"])

        assert result.exit_code == 0
        assert "Documentation generated" in result.output
        assert (tmp_path / ".qaagent" / "appdoc.json").exists()

    def test_generate_reports_counts(self, tmp_path):
        entry, profile = _mock_active_profile(path=str(tmp_path))

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_DISCOVER_ROUTES, return_value=[]):
            result = runner.invoke(app, ["doc", "generate", "--no-llm"])

        assert "Features:" in result.output
        assert "Routes:" in result.output

    def test_generate_no_active_target(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with patch(_PATCH_LOAD_PROFILE, side_effect=RuntimeError("No active")), \
             patch(_PATCH_DISCOVER_ROUTES, return_value=[]):
            result = runner.invoke(app, ["doc", "generate", "--no-llm"])

        assert result.exit_code == 0


class TestDocShow:
    def test_show_full(self):
        entry, profile = _mock_active_profile()

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            result = runner.invoke(app, ["doc", "show"])

        assert result.exit_code == 0
        assert "Test App" in result.output
        assert "Users" in result.output
        assert "Redis" in result.output

    def test_show_features_only(self):
        entry, profile = _mock_active_profile()

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            result = runner.invoke(app, ["doc", "show", "--section", "features"])

        assert result.exit_code == 0
        assert "Users" in result.output

    def test_show_no_doc(self):
        entry, profile = _mock_active_profile()

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_LOAD_DOC, return_value=None):
            result = runner.invoke(app, ["doc", "show"])

        assert result.exit_code == 1
        assert "No documentation found" in result.output


class TestDocExport:
    def test_export_markdown(self, tmp_path):
        entry, profile = _mock_active_profile(path=str(tmp_path))
        output_file = tmp_path / "output.md"

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            result = runner.invoke(app, ["doc", "export", "--format", "markdown", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "# Test App Documentation" in content

    def test_export_json(self, tmp_path):
        entry, profile = _mock_active_profile(path=str(tmp_path))
        output_file = tmp_path / "output.json"

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            result = runner.invoke(app, ["doc", "export", "--format", "json", "--output", str(output_file)])

        assert result.exit_code == 0
        data = json.loads(output_file.read_text())
        assert data["app_name"] == "Test App"

    def test_export_no_doc(self):
        entry, profile = _mock_active_profile()

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_LOAD_DOC, return_value=None):
            result = runner.invoke(app, ["doc", "export"])

        assert result.exit_code == 1
        assert "No documentation found" in result.output

    def test_export_invalid_format(self):
        entry, profile = _mock_active_profile()

        with patch(_PATCH_LOAD_PROFILE, return_value=(entry, profile)), \
             patch(_PATCH_LOAD_DOC, return_value=_sample_doc()):
            result = runner.invoke(app, ["doc", "export", "--format", "xml"])

        assert result.exit_code == 1
        assert "Unknown format" in result.output
