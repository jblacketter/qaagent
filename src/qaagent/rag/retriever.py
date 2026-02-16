"""Retrieval utilities for local RAG index queries."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Sequence

from .models import RagSearchResult

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def load_index(index_path: Path) -> Dict[str, object]:
    """Load a JSON index from disk."""
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid index format")
    return data


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text or "")]


def _score_chunk(chunk: Dict[str, object], query_tokens: Sequence[str]) -> float:
    if not query_tokens:
        return 0.0
    text = str(chunk.get("text", "")).lower()
    path = str(chunk.get("path", "")).lower()
    score = 0.0
    for token in query_tokens:
        if token in text:
            score += 1.0
        if token in path:
            score += 0.5
    return score


def search_index(
    index: Dict[str, object],
    query: str,
    *,
    top_k: int = 5,
) -> List[RagSearchResult]:
    """Search chunks with lexical scoring and deterministic ordering."""
    chunks = index.get("chunks", [])
    if not isinstance(chunks, list):
        return []

    query_tokens = _tokenize(query)
    scored: List[RagSearchResult] = []
    for raw in chunks:
        if not isinstance(raw, dict):
            continue
        score = _score_chunk(raw, query_tokens)
        if score <= 0:
            continue
        scored.append(
            RagSearchResult(
                chunk_id=str(raw.get("chunk_id", "")),
                path=str(raw.get("path", "")),
                score=round(score, 4),
                text=str(raw.get("text", "")),
                start_line=int(raw.get("start_line", 1)),
                end_line=int(raw.get("end_line", 1)),
                metadata=dict(raw.get("metadata", {}) or {}),
            ),
        )

    scored.sort(key=lambda item: (-item.score, item.path, item.start_line, item.chunk_id))
    return scored[: max(1, top_k)]

