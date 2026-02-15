"""Data models for local RAG indexing and retrieval."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any


@dataclass
class RagDocument:
    """A source document captured during indexing."""

    path: str
    source_type: str = "file"
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RagChunk:
    """A chunk of a source document used for retrieval."""

    chunk_id: str
    path: str
    text: str
    start_line: int
    end_line: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RagSearchResult:
    """A ranked retrieval result."""

    chunk_id: str
    path: str
    score: float
    text: str
    start_line: int
    end_line: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

