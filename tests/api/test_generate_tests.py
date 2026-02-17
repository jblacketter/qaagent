"""Regression test for POST /api/commands/generate-tests (Phase 18).

Ensures the endpoint uses GenerationResult.file_count instead of len(GenerationResult).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from qaagent.generators.base import GenerationResult


@pytest.fixture()
def client():
    from qaagent.web_ui import app
    return TestClient(app)


def _make_generation_result(file_count: int = 3) -> GenerationResult:
    """Create a GenerationResult with the given number of files."""
    files = {f"test_{i}.py": Path(f"/tmp/tests/test_{i}.py") for i in range(file_count)}
    return GenerationResult(files=files, stats={"tests": file_count * 2})


@patch("qaagent.web_ui.UnitTestGenerator")
@patch("qaagent.web_ui.NextJsRouteDiscoverer")
@patch("qaagent.web_ui.Workspace")
@patch("qaagent.web_ui.TargetManager")
def test_generate_tests_returns_file_count(
    mock_target_mgr_cls,
    mock_workspace_cls,
    mock_discoverer_cls,
    mock_generator_cls,
    client: TestClient,
):
    """POST /api/commands/generate-tests returns integer files count from GenerationResult.file_count."""
    # Mock TargetManager.get() → returns a target entry
    mock_entry = MagicMock()
    mock_entry.resolved_path.return_value = Path("/fake/repo")
    mock_target_mgr_cls.return_value.get.return_value = mock_entry

    # Mock Workspace.get_tests_dir() → returns a path
    mock_workspace_cls.return_value.get_tests_dir.return_value = Path("/fake/tests")

    # Mock route discovery → returns a list of fake routes
    mock_discoverer_cls.return_value.discover.return_value = [MagicMock(), MagicMock()]

    # Mock generator.generate() → returns a GenerationResult (NOT a list)
    expected_count = 5
    mock_generator_cls.return_value.generate.return_value = _make_generation_result(expected_count)

    response = client.post("/api/commands/generate-tests", json={
        "target": "test-repo",
        "command": "generate-tests",
        "params": {},
    })

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["files"] == expected_count
    assert isinstance(body["files"], int)


@patch("qaagent.web_ui.UnitTestGenerator")
@patch("qaagent.web_ui.NextJsRouteDiscoverer")
@patch("qaagent.web_ui.Workspace")
@patch("qaagent.web_ui.TargetManager")
def test_generate_tests_zero_files(
    mock_target_mgr_cls,
    mock_workspace_cls,
    mock_discoverer_cls,
    mock_generator_cls,
    client: TestClient,
):
    """Endpoint handles GenerationResult with zero files correctly."""
    mock_entry = MagicMock()
    mock_entry.resolved_path.return_value = Path("/fake/repo")
    mock_target_mgr_cls.return_value.get.return_value = mock_entry
    mock_workspace_cls.return_value.get_tests_dir.return_value = Path("/fake/tests")
    mock_discoverer_cls.return_value.discover.return_value = []
    mock_generator_cls.return_value.generate.return_value = _make_generation_result(0)

    response = client.post("/api/commands/generate-tests", json={
        "target": "test-repo",
        "command": "generate-tests",
        "params": {},
    })

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["files"] == 0


@patch("qaagent.web_ui.TargetManager")
def test_generate_tests_target_not_found(
    mock_target_mgr_cls,
    client: TestClient,
):
    """Endpoint returns 404 when target is not found."""
    mock_target_mgr_cls.return_value.get.return_value = None

    response = client.post("/api/commands/generate-tests", json={
        "target": "nonexistent",
        "command": "generate-tests",
        "params": {},
    })

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
