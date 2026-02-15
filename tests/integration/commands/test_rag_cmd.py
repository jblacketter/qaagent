"""Integration tests for RAG CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from qaagent.commands import app

runner = CliRunner()


def _seed_repo(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "service.py").write_text(
        "def create_pet(payload):\n    return {'id': 1, 'name': payload['name']}\n",
        encoding="utf-8",
    )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "api.md").write_text("Create pet endpoint returns JSON payload.\n", encoding="utf-8")


def test_rag_index_json_out(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    with patch("qaagent.commands.rag_cmd.load_active_profile", side_effect=RuntimeError("no active target")):
        result = runner.invoke(app, ["rag", "index", "--path", str(tmp_path), "--json-out"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["documents"] == 2
    assert payload["chunks"] >= 2
    assert Path(payload["index_path"]).exists()


def test_rag_query_json_out(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    with patch("qaagent.commands.rag_cmd.load_active_profile", side_effect=RuntimeError("no active target")):
        index_result = runner.invoke(app, ["rag", "index", "--path", str(tmp_path)])
    assert index_result.exit_code == 0

    with patch("qaagent.commands.rag_cmd.load_active_profile", side_effect=RuntimeError("no active target")):
        result = runner.invoke(
            app,
            ["rag", "query", "create pet payload", "--path", str(tmp_path), "--json-out", "--top-k", "2"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["count"] >= 1
    assert payload["results"][0]["path"] in {"docs/api.md", "src/service.py"}


def test_rag_query_missing_index_returns_exit_2(tmp_path: Path) -> None:
    with patch("qaagent.commands.rag_cmd.load_active_profile", side_effect=RuntimeError("no active target")):
        result = runner.invoke(app, ["rag", "query", "anything", "--path", str(tmp_path)])

    assert result.exit_code == 2
    assert "RAG index not found" in result.output
