"""Unit tests for fix API routes."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from qaagent.api.app import create_app
from qaagent.evidence import (
    EvidenceIDGenerator,
    EvidenceWriter,
    FindingRecord,
)
from qaagent.evidence.run_manager import RunManager


def _seed_run_with_findings(runs_dir: Path, repo: Path, tool: str = "flake8", count: int = 3) -> str:
    """Create a run with quality findings."""
    manager = RunManager(base_dir=runs_dir)
    repo.mkdir(parents=True, exist_ok=True)
    handle = manager.create_run("test-repo", repo)
    writer = EvidenceWriter(handle)
    id_gen = EvidenceIDGenerator(handle.run_id)

    records = []
    for i in range(count):
        records.append(
            FindingRecord(
                evidence_id=id_gen.next_id("fnd"),
                tool=tool,
                severity="high" if i == 0 else "medium",
                code=f"E30{i}",
                message=f"Issue {i}",
                file=f"src/file{i}.py",
                line=i + 1,
                column=1,
            ).to_dict()
        )

    writer.write_records("quality", records)
    return handle.run_id


@pytest.fixture()
def app_with_findings(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    repo = tmp_path / "repo"
    monkeypatch.setenv("QAAGENT_RUNS_DIR", str(runs_dir))
    run_id = _seed_run_with_findings(runs_dir, repo, tool="flake8", count=3)
    app = create_app()
    client = TestClient(app)
    yield client, run_id, repo


@pytest.fixture()
def app_empty_run(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    repo = tmp_path / "repo"
    monkeypatch.setenv("QAAGENT_RUNS_DIR", str(runs_dir))
    manager = RunManager(base_dir=runs_dir)
    repo.mkdir(parents=True, exist_ok=True)
    handle = manager.create_run("test-repo", repo)
    app = create_app()
    client = TestClient(app)
    yield client, handle.run_id


class TestGetFixableIssues:
    def test_returns_flake8_category(self, app_with_findings):
        client, run_id, _ = app_with_findings
        resp = client.get(f"/api/runs/{run_id}/fixable-issues")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_fixable_issues"] == 3
        assert data["total_fixable_files"] == 3
        cats = data["categories"]
        assert len(cats) == 1
        assert cats[0]["category"] == "formatting"
        assert cats[0]["tool"] == "autopep8"
        assert cats[0]["auto_fixable"] is True

    def test_empty_run(self, app_empty_run):
        client, run_id = app_empty_run
        resp = client.get(f"/api/runs/{run_id}/fixable-issues")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_fixable_issues"] == 0
        assert data["categories"] == []

    def test_not_found(self, app_with_findings):
        client, _, _ = app_with_findings
        resp = client.get("/api/runs/nonexistent/fixable-issues")
        assert resp.status_code == 404

    def test_bandit_findings_not_auto_fixable(self, tmp_path, monkeypatch):
        runs_dir = tmp_path / "runs"
        repo = tmp_path / "repo"
        monkeypatch.setenv("QAAGENT_RUNS_DIR", str(runs_dir))
        run_id = _seed_run_with_findings(runs_dir, repo, tool="bandit", count=2)
        app = create_app()
        client = TestClient(app)
        resp = client.get(f"/api/runs/{run_id}/fixable-issues")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_fixable_issues"] == 0
        assert data["total_manual_files"] == 2
        cats = data["categories"]
        assert len(cats) == 1
        assert cats[0]["auto_fixable"] is False


class TestApplyFix:
    def test_success(self, app_with_findings):
        client, run_id, repo = app_with_findings
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.files_modified = 2
        mock_result.errors = []
        with patch("qaagent.api.routes.fix.AutoFixer") as MockFixer, \
             patch("qaagent.api.routes.fix.Flake8Collector"):
            MockFixer.return_value.fix_formatting.return_value = mock_result
            resp = client.post(f"/api/runs/{run_id}/apply-fix", json={
                "category": "formatting",
                "tool": "autopep8",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["files_modified"] == 2

    def test_no_changes(self, app_with_findings):
        client, run_id, repo = app_with_findings
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.files_modified = 0
        mock_result.errors = []
        with patch("qaagent.api.routes.fix.AutoFixer") as MockFixer:
            MockFixer.return_value.fix_formatting.return_value = mock_result
            resp = client.post(f"/api/runs/{run_id}/apply-fix", json={
                "category": "formatting",
                "tool": "autopep8",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_changes"

    def test_invalid_category(self, app_with_findings):
        client, run_id, _ = app_with_findings
        resp = client.post(f"/api/runs/{run_id}/apply-fix", json={
            "category": "invalid",
            "tool": "autopep8",
        })
        assert resp.status_code == 400
        assert "Invalid category" in resp.json()["detail"]

    def test_not_found(self, app_with_findings):
        client, _, _ = app_with_findings
        resp = client.post("/api/runs/nonexistent/apply-fix", json={
            "category": "formatting",
            "tool": "autopep8",
        })
        assert resp.status_code == 404
