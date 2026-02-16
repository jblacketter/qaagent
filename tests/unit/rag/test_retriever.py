"""Unit tests for local RAG retrieval."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qaagent.rag.retriever import load_index, search_index


def test_load_index_rejects_non_object_payload(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    path.write_text('["not", "an", "object"]', encoding="utf-8")

    with pytest.raises(ValueError):
        load_index(path)


def test_search_index_ranks_by_score_and_path_tiebreak() -> None:
    index = {
        "chunks": [
            {
                "chunk_id": "src/a.py:1",
                "path": "src/a.py",
                "text": "pets endpoint validates payload",
                "start_line": 1,
                "end_line": 2,
            },
            {
                "chunk_id": "src/b.py:1",
                "path": "src/b.py",
                "text": "pets endpoint",
                "start_line": 1,
                "end_line": 1,
            },
            {
                "chunk_id": "docs/api.md:1",
                "path": "docs/api.md",
                "text": "pets endpoint validates payload",
                "start_line": 1,
                "end_line": 2,
            },
        ],
    }

    results = search_index(index, "pets validates", top_k=3)

    assert len(results) == 3
    assert results[0].path == "docs/api.md"
    assert results[1].path == "src/a.py"
    assert results[0].score >= results[2].score


def test_search_index_handles_invalid_chunks() -> None:
    index = {"chunks": ["bad-entry", {"chunk_id": "x", "path": "src/x.py", "text": "alpha", "start_line": 1, "end_line": 1}]}

    results = search_index(index, "alpha", top_k=5)

    assert len(results) == 1
    assert results[0].chunk_id == "x"


def test_load_index_roundtrip(tmp_path: Path) -> None:
    payload = {"version": 1, "chunks": []}
    path = tmp_path / "index.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    data = load_index(path)

    assert data["version"] == 1
