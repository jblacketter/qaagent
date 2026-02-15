"""Unit tests for the local RAG indexer."""

from __future__ import annotations

import json
from pathlib import Path

from qaagent.rag.indexer import _chunk_text, default_index_path, index_repository


def test_chunk_text_preserves_line_ranges() -> None:
    text = "alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot\n"
    chunks = _chunk_text(text, chunk_chars=14)

    assert chunks == [
        (1, 2, "alpha\nbravo"),
        (3, 4, "charlie\ndelta"),
        (5, 6, "echo\nfoxtrot"),
    ]


def test_index_repository_writes_default_index(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "src" / "app.py").write_text("def ping():\n    return 'pong'\n", encoding="utf-8")
    (tmp_path / "docs" / "README.md").write_text("# Service\nAPI notes\n", encoding="utf-8")

    summary = index_repository(tmp_path, chunk_chars=20, max_file_bytes=100_000)
    index_path = default_index_path(tmp_path)

    assert summary["index_path"] == index_path.as_posix()
    assert summary["documents"] == 2
    assert summary["chunks"] >= 2
    assert index_path.exists()

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["root"] == tmp_path.resolve().as_posix()
    assert {doc["path"] for doc in payload["documents"]} == {"docs/README.md", "src/app.py"}


def test_index_repository_excludes_dirs_and_large_files(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "src" / "keep.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "src" / "too_big.py").write_text("x" * 1024, encoding="utf-8")
    (tmp_path / "node_modules" / "skip.py").write_text("print('nope')\n", encoding="utf-8")

    summary = index_repository(tmp_path, max_file_bytes=128)

    assert summary["documents"] == 1
    payload = json.loads(default_index_path(tmp_path).read_text(encoding="utf-8"))
    assert [doc["path"] for doc in payload["documents"]] == ["src/keep.py"]
