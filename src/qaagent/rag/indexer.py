"""Local repository indexer for retrieval-augmented generation."""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .models import RagChunk, RagDocument

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".next",
}

DEFAULT_INCLUDE_EXTS = {
    ".py",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".feature",
    ".sql",
}


def default_index_path(root: Path) -> Path:
    """Return canonical on-disk index location for a project root."""
    return root / ".qaagent" / "rag" / "index.json"


def _iter_files(
    root: Path,
    include_exts: Iterable[str],
    exclude_dirs: Iterable[str],
    max_file_bytes: int,
) -> Iterable[Path]:
    include = {ext.lower() for ext in include_exts}
    excluded = set(exclude_dirs)

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() not in include:
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
        except OSError:
            continue
        yield path


def _chunk_text(text: str, *, chunk_chars: int) -> List[Tuple[int, int, str]]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks: List[Tuple[int, int, str]] = []
    start = 0
    while start < len(lines):
        size = 0
        end = start
        while end < len(lines):
            next_len = len(lines[end]) + 1
            if end > start and size + next_len > chunk_chars:
                break
            size += next_len
            end += 1
            if size >= chunk_chars:
                break

        text_chunk = "\n".join(lines[start:end]).strip()
        if text_chunk:
            chunks.append((start + 1, end, text_chunk))
        start = end
    return chunks


def index_repository(
    root: Path,
    *,
    output_path: Optional[Path] = None,
    chunk_chars: int = 1400,
    max_file_bytes: int = 500_000,
    include_exts: Optional[Iterable[str]] = None,
    exclude_dirs: Optional[Iterable[str]] = None,
) -> Dict[str, object]:
    """Index a repository and persist chunked context to disk."""
    root = root.resolve()
    include = include_exts or DEFAULT_INCLUDE_EXTS
    exclude = exclude_dirs or DEFAULT_EXCLUDE_DIRS

    documents: List[RagDocument] = []
    chunks: List[RagChunk] = []

    for file_path in _iter_files(root, include, exclude, max_file_bytes):
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        rel = file_path.relative_to(root).as_posix()
        documents.append(
            RagDocument(
                path=rel,
                size_bytes=len(text.encode("utf-8", errors="ignore")),
            ),
        )

        for idx, (start_line, end_line, text_chunk) in enumerate(
            _chunk_text(text, chunk_chars=chunk_chars),
            start=1,
        ):
            chunks.append(
                RagChunk(
                    chunk_id=f"{rel}:{idx}",
                    path=rel,
                    text=text_chunk,
                    start_line=start_line,
                    end_line=end_line,
                ),
            )

    out_path = output_path or default_index_path(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": 1,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "root": root.as_posix(),
        "documents": [doc.to_dict() for doc in documents],
        "chunks": [chunk.to_dict() for chunk in chunks],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "index_path": out_path.as_posix(),
        "documents": len(documents),
        "chunks": len(chunks),
        "root": root.as_posix(),
    }
