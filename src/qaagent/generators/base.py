"""Base generator infrastructure for all test generators.

Provides BaseGenerator ABC, GenerationResult dataclass, and syntax validation utilities.
"""
from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from qaagent.analyzers.models import Risk, Route
from qaagent.config.models import LLMSettings


@dataclass
class GenerationResult:
    """Result of a test generation run."""

    files: Dict[str, Path] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    llm_used: bool = False

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def test_count(self) -> int:
        return self.stats.get("tests", 0)


def validate_python_syntax(code: str) -> tuple[bool, Optional[str]]:
    """Validate Python code syntax via ast.parse().

    Returns:
        (True, None) if valid, (False, error_message) if invalid.
    """
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as exc:
        msg = f"Line {exc.lineno}: {exc.msg}" if exc.lineno else str(exc.msg)
        return False, msg


class BaseGenerator(ABC):
    """Abstract base for all test generators.

    Provides a uniform constructor and interface. Subclasses implement generate().
    """

    def __init__(
        self,
        routes: List[Route],
        risks: Optional[List[Risk]] = None,
        output_dir: Optional[Path] = None,
        base_url: str = "http://localhost:8000",
        project_name: str = "Application",
        llm_settings: Optional[LLMSettings] = None,
        retrieval_context: Optional[List[str]] = None,
    ) -> None:
        self.routes = list(routes)
        self.risks = list(risks) if risks else []
        self.output_dir = Path(output_dir) if output_dir else Path("tests/qaagent")
        self.base_url = base_url
        self.project_name = project_name
        self.llm_settings = llm_settings
        self.retrieval_context = list(retrieval_context) if retrieval_context else []

    @property
    def llm_enabled(self) -> bool:
        """Whether LLM enhancement is configured and enabled."""
        return bool(self.llm_settings and self.llm_settings.enabled)

    @abstractmethod
    def generate(self, **kwargs: Any) -> GenerationResult:
        """Generate test files. Returns a GenerationResult."""
        ...
