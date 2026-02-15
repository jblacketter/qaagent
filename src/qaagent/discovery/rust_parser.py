"""Rust route discovery for Actix Web and Axum projects."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from qaagent.analyzers.models import Route

from .base import FrameworkParser, RouteParam

_HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
_SKIP_DIRS = {"target", ".git", "node_modules", "__pycache__"}


class RustParser(FrameworkParser):
    """Discover routes from Rust source files."""

    framework_name = "rust"

    def parse(self, source_dir: Path) -> List[Route]:
        routes: List[Route] = []
        for rs_file in self.find_route_files(source_dir):
            try:
                content = rs_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = str(rs_file.relative_to(source_dir))
            routes.extend(self._parse_file(content, rel))
        return routes

    def find_route_files(self, source_dir: Path) -> List[Path]:
        candidates: List[Path] = []
        for rs_file in sorted(source_dir.rglob("*.rs")):
            rel = rs_file.relative_to(source_dir)
            if any(part in _SKIP_DIRS for part in rel.parts):
                continue
            if any(part in {"tests", "benches"} for part in rel.parts):
                continue
            try:
                content = rs_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if any(token in content for token in ("#[get(", "#[post(", ".route(", "axum", "actix_web", "web::")):
                candidates.append(rs_file)
        return candidates

    def _parse_file(self, content: str, rel_file: str) -> List[Route]:
        routes: List[Route] = []

        macro_pattern = re.compile(
            r'#\[\s*(?:[A-Za-z_][\w:]*::)?(get|post|put|patch|delete|head|options)\s*\(\s*"([^"]+)"',
            re.IGNORECASE,
        )
        for match in macro_pattern.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            window = content[max(0, match.start() - 180) : min(len(content), match.end() + 180)]
            routes.append(
                self._build_route(
                    path=path,
                    method=method,
                    auth_required=self._contains_auth(window),
                    framework="actix",
                    rel_file=rel_file,
                ),
            )

        actix_route_pattern = re.compile(
            r'\.route\(\s*"([^"]+)"\s*,\s*web::(get|post|put|patch|delete|head|options)\s*\(\)',
            re.IGNORECASE,
        )
        for match in actix_route_pattern.finditer(content):
            routes.append(
                self._build_route(
                    path=match.group(1),
                    method=match.group(2).upper(),
                    auth_required=self._contains_auth(match.group(0)),
                    framework="actix",
                    rel_file=rel_file,
                ),
            )

        # Generic Router::route(...) extraction for Axum-style APIs.
        for path, handler_expr in self._extract_route_calls(content):
            if "web::" in handler_expr:
                continue
            methods = self._extract_methods_from_handler(handler_expr)
            if not methods:
                continue
            framework = "axum" if "axum" in content.lower() or "router::new" in content.lower() else "rust"
            auth_required = self._contains_auth(handler_expr)
            for method in methods:
                routes.append(
                    self._build_route(
                        path=path,
                        method=method,
                        auth_required=auth_required,
                        framework=framework,
                        rel_file=rel_file,
                    ),
                )

        return routes

    def _build_route(
        self,
        *,
        path: str,
        method: str,
        auth_required: bool,
        framework: str,
        rel_file: str,
    ) -> Route:
        normalized_path = self._normalize_path(path)
        path_params = self._extract_path_params(normalized_path)
        params: Dict[str, List[RouteParam]] = {"path": path_params} if path_params else {}

        return self._normalize_route(
            path=normalized_path,
            method=method,
            params=params,
            auth_required=auth_required,
            metadata={
                "source": "rust",
                "framework": framework,
                "file": rel_file,
            },
            confidence=0.85,
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        out = (path or "/").strip()
        out = re.sub(r"\*([A-Za-z_]\w*)", r"{\1}", out)
        out = re.sub(r"\*", "{wildcard}", out)
        out = re.sub(r"/+", "/", out)
        if not out.startswith("/"):
            out = "/" + out
        return out

    @staticmethod
    def _extract_path_params(path: str) -> List[RouteParam]:
        names = set(re.findall(r":([A-Za-z_]\w*)", path))
        names.update(re.findall(r"\{([A-Za-z_]\w*)\}", path))
        return [RouteParam(name=name, type="string", required=True) for name in sorted(names)]

    @staticmethod
    def _contains_auth(text: str) -> bool:
        lowered = text.lower()
        return any(
            token in lowered
            for token in (
                "auth",
                "jwt",
                "token",
                "session",
                "requireauthorizationlayer",
                "middleware::from_fn",
            )
        )

    def _extract_methods_from_handler(self, handler_expr: str) -> List[str]:
        methods: List[str] = []
        lowered = handler_expr.lower()
        for method in _HTTP_METHODS:
            if re.search(rf"\b{method.lower()}\s*\(", lowered):
                methods.append(method)
        if not methods and re.search(r"\bany\s*\(", lowered):
            return list(_HTTP_METHODS)
        return sorted(set(methods))

    def _extract_route_calls(self, content: str) -> List[Tuple[str, str]]:
        """Extract `.route(path, handler_expr)` calls with balanced parentheses."""
        calls: List[Tuple[str, str]] = []
        needle = ".route("
        idx = 0

        while True:
            start = content.find(needle, idx)
            if start == -1:
                break
            i = start + len(needle)
            depth = 1
            in_string = False
            quote = ""
            escaped = False

            while i < len(content):
                ch = content[i]
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == quote:
                        in_string = False
                else:
                    if ch in ("'", '"'):
                        in_string = True
                        quote = ch
                    elif ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            break
                i += 1

            args = content[start + len(needle) : i]
            path, handler_expr = self._split_route_args(args)
            if path and handler_expr:
                calls.append((path, handler_expr))
            idx = i + 1

        return calls

    @staticmethod
    def _split_route_args(args: str) -> tuple[Optional[str], Optional[str]]:
        depth = 0
        in_string = False
        quote = ""
        escaped = False
        split_idx: Optional[int] = None

        for i, ch in enumerate(args):
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    in_string = False
                continue
            if ch in ("'", '"'):
                in_string = True
                quote = ch
                continue
            if ch == "(":
                depth += 1
                continue
            if ch == ")":
                depth -= 1
                continue
            if ch == "," and depth == 0:
                split_idx = i
                break

        if split_idx is None:
            return None, None

        left = args[:split_idx].strip()
        right = args[split_idx + 1 :].strip()

        # "path", r"path", r#"path"# raw strings
        string_match = re.match(r'^(?:r#*|)(["\'])(.*)\1#*$', left)
        if not string_match:
            return None, None
        return string_match.group(2), right
