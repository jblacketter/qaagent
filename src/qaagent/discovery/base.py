"""Base classes for framework route parsers."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel

from qaagent.analyzers.models import Route, RouteSource


class RouteParam(BaseModel):
    """Internal validation model for parser output.

    Serialized to dict via .model_dump() for Route.params entries.
    """

    name: str
    type: str = "string"
    required: bool = True


class FrameworkParser(ABC):
    """Abstract base for framework-specific route parsers."""

    framework_name: str = ""

    @abstractmethod
    def parse(self, source_dir: Path) -> List[Route]:
        """Parse source directory and return discovered routes."""
        ...

    @abstractmethod
    def find_route_files(self, source_dir: Path) -> List[Path]:
        """Find files that may contain route definitions."""
        ...

    def _normalize_route(
        self,
        path: str,
        method: str,
        params: Dict[str, List[RouteParam]],
        auth_required: bool,
        *,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        responses: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        confidence: float = 0.9,
    ) -> Route:
        """Build a Route with normalized fields.

        - Converts :param and <param> to {param} in path
        - Converts <type:param> (Flask/Django) to {param}
        - Serializes RouteParam objects to dicts via .model_dump()
        - Returns Route compatible with existing consumers
        """
        # Normalize path parameters: <type:name> -> {name}, <name> -> {name}, :name -> {name}
        normalized_path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", path)
        normalized_path = re.sub(r":(\w+)", r"{\1}", normalized_path)

        serialized_params: Dict[str, list] = {
            location: [p.model_dump() for p in param_list]
            for location, param_list in params.items()
        }

        return Route(
            path=normalized_path,
            method=method.upper(),
            auth_required=auth_required,
            summary=summary or f"{method.upper()} {normalized_path}",
            description=description,
            tags=tags or [self._extract_tag(normalized_path)],
            params=serialized_params,
            responses=responses or {"200": {"description": "Success"}},
            source=RouteSource.CODE,
            confidence=confidence,
            metadata=metadata or {},
        )

    @staticmethod
    def _extract_tag(path: str) -> str:
        """Extract a tag from the first non-version, non-param path segment."""
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        for part in parts:
            if not re.match(r"^v\d+$", part):
                return part
        return parts[0] if parts else "api"
