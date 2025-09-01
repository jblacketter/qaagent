from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import json
import re


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


@dataclass
class Operation:
    method: str
    path: str
    operation_id: Optional[str]
    tags: List[str]


def is_url(target: str) -> bool:
    return target.startswith("http://") or target.startswith("https://")


def _read_text(path_or_url: str) -> str:
    if is_url(path_or_url):
        try:
            import httpx  # type: ignore

            r = httpx.get(path_or_url, timeout=15.0)
            r.raise_for_status()
            return r.text
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "Unable to fetch OpenAPI from URL. Install API extras and check network: pip install -e .[api]"
            ) from e
    else:
        p = Path(path_or_url)
        return p.read_text(encoding="utf-8")


def load_openapi(path_or_url: str) -> Dict:
    text = _read_text(path_or_url)
    # Try JSON first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Then YAML
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Unable to parse OpenAPI spec; ensure JSON or YAML. For YAML, install PyYAML: pip install -e .[api]"
        ) from e


def enumerate_operations(spec: Dict) -> List[Operation]:
    ops: List[Operation] = []
    paths = spec.get("paths", {}) or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in HTTP_METHODS:
                continue
            op_id = None
            tags: List[str] = []
            if isinstance(op, dict):
                op_id = op.get("operationId")
                tags = list(op.get("tags", []) or [])
            ops.append(Operation(method=method.upper(), path=path, operation_id=op_id, tags=tags))
    return ops


def find_openapi_candidates(root: str | Path = ".") -> List[Path]:
    root = Path(root)
    names = [
        "openapi.yaml",
        "openapi.yml",
        "openapi.json",
        "swagger.yaml",
        "swagger.yml",
        "swagger.json",
    ]
    candidates = [p for name in names for p in root.glob(f"**/{name}")]
    # Also a heuristic scan for small repos
    if not candidates:
        for p in root.glob("**/*.yaml"):
            try:
                head = p.read_text(encoding="utf-8").splitlines()[:5]
                if any(line.strip().startswith("openapi:") for line in head):
                    candidates.append(p)
            except Exception:
                continue
    return sorted(set(candidates))


def probe_spec_from_base_url(base_url: str) -> Optional[str]:
    # Common endpoints used by frameworks
    suffixes = [
        "/openapi.json",
        "/openapi.yaml",
        "/swagger.json",
        "/v3/api-docs",
        "/swagger/v1/swagger.json",
    ]
    try:
        import httpx  # type: ignore

        for s in suffixes:
            url = base_url.rstrip("/") + s
            try:
                r = httpx.get(url, timeout=8.0)
                if r.status_code == 200 and r.text:
                    return url
            except Exception:
                continue
    except Exception:
        return None
    return None


def covered_operations_from_junit_case_names(case_names: Iterable[str]) -> List[Tuple[str, str]]:
    """Best-effort extraction of (METHOD, PATH) from Schemathesis-style test names.

    Matches patterns like "GET /users" within the case names.
    """
    results: List[Tuple[str, str]] = []
    pattern = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b\s+([^\s\]]+)")
    for name in case_names:
        m = pattern.search(name)
        if m:
            results.append((m.group(1).upper(), m.group(2)))
    return results

