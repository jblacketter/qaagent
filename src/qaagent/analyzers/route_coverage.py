"""Route-level coverage gap analysis.

Provides a single source of truth for API operation coverage calculations
that can be reused by report generation and CLI commands.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from qaagent.analyzers.models import Route
from qaagent.openapi_utils import (
    covered_operations_from_junit_case_names,
    enumerate_operations,
    load_openapi,
)

_UUID_SEGMENT_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    flags=re.IGNORECASE,
)
_INT_SEGMENT_RE = re.compile(r"^\d+$")
_DYNAMIC_SEGMENT_RE = re.compile(r"^(\{[^{}]+\}|:[^/]+|\[[^\]]+\]|<[^>]+>)$")

_SENSITIVE_PATH_SEGMENTS = {
    "admin",
    "auth",
    "internal",
    "billing",
    "payment",
    "payments",
    "token",
    "tokens",
    "secret",
    "secrets",
}
_SENSITIVE_TAGS = {
    "admin",
    "auth",
    "authentication",
    "authorization",
    "billing",
    "payment",
    "payments",
    "security",
    "internal",
}
_PRIORITY_SCORE = {"high": 3, "medium": 2, "low": 1}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass(frozen=True)
class CoverageOperation:
    """Canonical operation used for coverage matching and gap output."""

    method: str
    path: str
    auth_required: bool = False
    tags: Tuple[str, ...] = ()
    source: str = "unknown"


def normalize_method(method: str) -> str:
    """Normalize HTTP method token."""
    return (method or "").strip().upper()


def normalize_path(path: str) -> str:
    """Normalize path tokens to a canonical templated representation."""
    raw = (path or "").strip()
    if not raw:
        return "/"
    raw = raw.split("?", 1)[0].split("#", 1)[0].strip()
    if not raw.startswith("/"):
        raw = "/" + raw
    raw = re.sub(r"/{2,}", "/", raw)
    if len(raw) > 1 and raw.endswith("/"):
        raw = raw[:-1]

    parts: List[str] = []
    for segment in raw.split("/"):
        if not segment:
            continue
        if _is_dynamic_segment(segment):
            parts.append("{param}")
        else:
            parts.append(segment)
    return "/" + "/".join(parts) if parts else "/"


def _is_dynamic_segment(segment: str) -> bool:
    if _DYNAMIC_SEGMENT_RE.match(segment):
        return True
    if _INT_SEGMENT_RE.match(segment):
        return True
    if _UUID_SEGMENT_RE.match(segment):
        return True
    return False


def canonical_operation_key(method: str, path: str) -> Tuple[str, str]:
    """Build canonical operation key."""
    return normalize_method(method), normalize_path(path)


def operations_from_routes(routes: Iterable[Route]) -> List[CoverageOperation]:
    """Convert discovered routes into canonical operations."""
    operations: List[CoverageOperation] = []
    for route in routes:
        method, path = canonical_operation_key(route.method, route.path)
        operations.append(
            CoverageOperation(
                method=method,
                path=path,
                auth_required=bool(route.auth_required),
                tags=tuple(sorted(set(route.tags or []))),
                source="routes",
            ),
        )
    return operations


def operations_from_openapi(openapi_path: str) -> Tuple[List[CoverageOperation], str]:
    """Load canonical operations from an OpenAPI spec."""
    spec = load_openapi(openapi_path)
    operations = enumerate_operations(spec)
    global_security = spec.get("security")
    path_items = spec.get("paths", {}) or {}

    converted: List[CoverageOperation] = []
    for operation in operations:
        method, path = canonical_operation_key(operation.method, operation.path)
        op_obj = (path_items.get(operation.path) or {}).get(operation.method.lower(), {})
        security = op_obj.get("security") if isinstance(op_obj, dict) else None
        if security is None:
            security = global_security
        # security: [] explicitly means "no auth required"
        auth_required = bool(security) if security != [] else False
        tags = tuple(sorted(set(operation.tags or [])))
        converted.append(
            CoverageOperation(
                method=method,
                path=path,
                auth_required=auth_required,
                tags=tags,
                source="openapi",
            ),
        )
    return converted, openapi_path


def load_case_names_from_junit(junit_files: Iterable[Path]) -> List[str]:
    """Load test case names from junit XML files/directories."""
    from qaagent.report import parse_junit

    case_names: List[str] = []
    expanded: List[Path] = []
    for path in junit_files:
        if not path.exists():
            continue
        if path.is_dir():
            expanded.extend(sorted(path.glob("*.xml")))
        else:
            expanded.append(path)

    for file in expanded:
        suites = parse_junit(file)
        for suite in suites:
            for case in suite.cases:
                if case.name:
                    case_names.append(case.name)
    return case_names


def _extract_covered_operations(
    case_names: Iterable[str],
    route_hints: Optional[Iterable[Tuple[str, str] | str]] = None,
) -> set[Tuple[str, str]]:
    covered: set[Tuple[str, str]] = set()

    for method, path in covered_operations_from_junit_case_names(case_names):
        covered.add(canonical_operation_key(method, path))

    for hint in route_hints or []:
        if isinstance(hint, tuple) and len(hint) == 2:
            method, path = hint
            covered.add(canonical_operation_key(method, path))
            continue
        if isinstance(hint, str):
            match = re.search(
                r"\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b\s+([^\s\]]+)",
                hint,
                flags=re.IGNORECASE,
            )
            if match:
                covered.add(canonical_operation_key(match.group(1), match.group(2)))
    return covered


def _merge_operation(
    merged: Dict[Tuple[str, str], CoverageOperation],
    operation: CoverageOperation,
) -> None:
    key = (operation.method, operation.path)
    existing = merged.get(key)
    if existing is None:
        merged[key] = operation
        return

    merged_tags = tuple(sorted(set(existing.tags + operation.tags)))
    merged[key] = CoverageOperation(
        method=existing.method,
        path=existing.path,
        auth_required=existing.auth_required or operation.auth_required,
        tags=merged_tags,
        source=existing.source,
    )


def _priority_for_operation(operation: CoverageOperation) -> Tuple[str, str]:
    tags = {tag.lower() for tag in operation.tags}
    static_segments = {
        segment.lower()
        for segment in operation.path.split("/")
        if segment and not segment.startswith("{")
    }

    if operation.auth_required:
        return "high", "auth-required route"
    if tags & _SENSITIVE_TAGS:
        return "high", "sensitive route tags"
    if static_segments & _SENSITIVE_PATH_SEGMENTS:
        return "high", "sensitive route path"
    if operation.method in _WRITE_METHODS:
        return "medium", "state-changing method"
    if "{param}" in operation.path:
        return "medium", "parameterized route"
    return "low", "read-oriented route"


def build_route_coverage(
    *,
    openapi_path: Optional[str] = None,
    routes: Optional[Iterable[Route]] = None,
    junit_files: Optional[Iterable[str | Path]] = None,
    case_names: Optional[Iterable[str]] = None,
    route_hints: Optional[Iterable[Tuple[str, str] | str]] = None,
) -> Dict[str, object] | None:
    """Compute route-level coverage summary and uncovered gap metadata."""
    merged_operations: Dict[Tuple[str, str], CoverageOperation] = {}
    spec_label: Optional[str] = None

    if openapi_path:
        openapi_operations, spec_label = operations_from_openapi(openapi_path)
        for operation in openapi_operations:
            _merge_operation(merged_operations, operation)

    if routes:
        for operation in operations_from_routes(routes):
            _merge_operation(merged_operations, operation)

    if not merged_operations:
        return None

    names = list(case_names or [])
    if not names and junit_files:
        paths = [Path(path) for path in junit_files]
        names = load_case_names_from_junit(paths)

    covered = _extract_covered_operations(names, route_hints=route_hints)

    ordered_ops = sorted(
        merged_operations.values(),
        key=lambda operation: (operation.method, operation.path),
    )
    covered_count = sum(
        1 for operation in ordered_ops if (operation.method, operation.path) in covered
    )
    total = len(ordered_ops)

    uncovered: List[Dict[str, object]] = []
    for operation in ordered_ops:
        if (operation.method, operation.path) in covered:
            continue
        priority, reason = _priority_for_operation(operation)
        uncovered.append(
            {
                "method": operation.method,
                "path": operation.path,
                "priority": priority,
                "priority_reason": reason,
                "auth_required": operation.auth_required,
                "tags": list(operation.tags),
                "source": operation.source,
            },
        )

    uncovered.sort(
        key=lambda item: (
            -_PRIORITY_SCORE.get(str(item["priority"]), 0),
            str(item["method"]),
            str(item["path"]),
        ),
    )
    uncovered_samples = [
        (str(item["method"]), str(item["path"]))
        for item in uncovered[:20]
    ]
    priority_samples = [
        {
            "priority": str(item["priority"]),
            "method": str(item["method"]),
            "path": str(item["path"]),
        }
        for item in uncovered[:10]
    ]

    return {
        "spec": spec_label,
        "covered": covered_count,
        "total": total,
        "pct": round((covered_count * 100.0 / total), 1) if total else 0.0,
        "covered_operations": sorted(list(covered)),
        "uncovered_samples": uncovered_samples,
        "priority_uncovered_samples": priority_samples,
        "uncovered": uncovered,
    }

