"""Go route discovery for net/http, Gin, and Echo projects."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from qaagent.analyzers.models import Route

from .base import FrameworkParser, RouteParam

_HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
_SKIP_DIRS = {"vendor", ".git", ".venv", "node_modules", "__pycache__", "dist", "build"}


class GoParser(FrameworkParser):
    """Discover routes from Go source files."""

    framework_name = "go"

    def parse(self, source_dir: Path) -> List[Route]:
        routes: List[Route] = []
        for go_file in self.find_route_files(source_dir):
            try:
                content = go_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = str(go_file.relative_to(source_dir))
            routes.extend(self._parse_file(content, rel))
        return routes

    def find_route_files(self, source_dir: Path) -> List[Path]:
        candidates: List[Path] = []
        for go_file in sorted(source_dir.rglob("*.go")):
            if go_file.name.endswith("_test.go"):
                continue
            rel = go_file.relative_to(source_dir)
            if any(part in _SKIP_DIRS for part in rel.parts):
                continue
            try:
                content = go_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if any(
                token in content
                for token in (
                    "HandleFunc(",
                    ".GET(",
                    ".POST(",
                    ".PUT(",
                    ".PATCH(",
                    ".DELETE(",
                    ".Group(",
                    "gin.",
                    "echo.",
                )
            ):
                candidates.append(go_file)
        return candidates

    def _parse_file(self, content: str, rel_file: str) -> List[Route]:
        routes: List[Route] = []
        var_prefixes: Dict[str, str] = {}
        var_auth: Dict[str, bool] = {}
        var_framework: Dict[str, str] = {}

        # Root router variables.
        for match in re.finditer(r"\b(?P<var>[A-Za-z_]\w*)\s*:?=\s*gin\.(?:Default|New)\(\)", content):
            var = match.group("var")
            var_prefixes[var] = ""
            var_auth[var] = False
            var_framework[var] = "gin"
        for match in re.finditer(r"\b(?P<var>[A-Za-z_]\w*)\s*:?=\s*echo\.New\(\)", content):
            var = match.group("var")
            var_prefixes[var] = ""
            var_auth[var] = False
            var_framework[var] = "echo"
        for match in re.finditer(r"\b(?P<var>[A-Za-z_]\w*)\s*:?=\s*http\.NewServeMux\(\)", content):
            var = match.group("var")
            var_prefixes[var] = ""
            var_auth[var] = False
            var_framework[var] = "nethttp"

        # Group prefixes for Gin/Echo.
        group_pattern = re.compile(
            r"\b(?P<var>[A-Za-z_]\w*)\s*:?=\s*(?P<base>[A-Za-z_]\w*)\.Group\("
            r'\s*"(?P<prefix>[^"]*)"(?:\s*,\s*(?P<middleware>[^)]*))?\)',
        )
        for match in group_pattern.finditer(content):
            var = match.group("var")
            base = match.group("base")
            prefix = match.group("prefix") or ""
            middleware = match.group("middleware") or ""

            base_prefix = var_prefixes.get(base, "")
            var_prefixes[var] = self._join_path(base_prefix, prefix)
            var_auth[var] = var_auth.get(base, False) or self._contains_auth(middleware)
            var_framework[var] = var_framework.get(base, "go")

        # net/http patterns.
        for pattern in (
            r"\b(?:http|[A-Za-z_]\w*)\.HandleFunc\(\s*\"([^\"]+)\"\s*,",
            r"\b(?:http|[A-Za-z_]\w*)\.Handle\(\s*\"([^\"]+)\"\s*,",
        ):
            for match in re.finditer(pattern, content):
                method, raw_path = self._parse_nethttp_pattern(match.group(1))
                routes.append(
                    self._build_route(
                        path=raw_path,
                        method=method,
                        auth_required=False,
                        framework="nethttp",
                        rel_file=rel_file,
                    ),
                )

        # Gin/Echo route methods.
        route_pattern = re.compile(
            r"\b(?P<var>[A-Za-z_]\w*)\.(?P<method>GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|Any)\("
            r'\s*"(?P<path>[^"]*)"(?:\s*,\s*(?P<handlers>[^)]*))?\)',
            re.IGNORECASE,
        )
        for match in route_pattern.finditer(content):
            var = match.group("var")
            method_token = match.group("method").upper()
            raw_path = match.group("path")
            handlers = match.group("handlers") or ""
            prefix = var_prefixes.get(var, "")

            methods = list(_HTTP_METHODS) if method_token == "ANY" else [method_token]
            full_path = self._join_path(prefix, raw_path)
            auth_required = var_auth.get(var, False) or self._contains_auth(handlers)
            framework = var_framework.get(var, "go")

            for method in methods:
                routes.append(
                    self._build_route(
                        path=full_path,
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
        normalized_path = self._normalize_go_path(path)
        path_params = self._extract_path_params(normalized_path)
        params: Dict[str, List[RouteParam]] = {"path": path_params} if path_params else {}

        return self._normalize_route(
            path=normalized_path,
            method=method,
            params=params,
            auth_required=auth_required,
            metadata={
                "source": "go",
                "framework": framework,
                "file": rel_file,
            },
            confidence=0.85,
        )

    @staticmethod
    def _parse_nethttp_pattern(spec: str) -> tuple[str, str]:
        """Parse Go 1.22 METHOD /path patterns, fallback to GET /path."""
        match = re.match(r"^\s*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(.+)$", spec, re.IGNORECASE)
        if match:
            return match.group(1).upper(), match.group(2).strip()
        return "GET", spec.strip()

    @staticmethod
    def _normalize_go_path(path: str) -> str:
        out = (path or "/").strip()
        out = re.sub(r"\*([A-Za-z_]\w*)", r"{\1}", out)
        out = re.sub(r"\*", "{wildcard}", out)
        out = re.sub(r"/+", "/", out)
        if not out.startswith("/"):
            out = "/" + out
        return out or "/"

    @staticmethod
    def _extract_path_params(path: str) -> List[RouteParam]:
        names = set(re.findall(r"\{([A-Za-z_]\w*)\}", path))
        names.update(re.findall(r":([A-Za-z_]\w*)", path))
        return [RouteParam(name=name, type="string", required=True) for name in sorted(names)]

    @staticmethod
    def _join_path(prefix: str, path: str) -> str:
        if not prefix and not path:
            return "/"
        if not prefix:
            out = path
        elif not path:
            out = prefix
        else:
            out = prefix.rstrip("/") + "/" + path.lstrip("/")
        out = re.sub(r"/+", "/", out)
        if not out.startswith("/"):
            out = "/" + out
        return out

    @staticmethod
    def _contains_auth(text: Optional[str]) -> bool:
        if not text:
            return False
        lowered = text.lower()
        return any(token in lowered for token in ("auth", "jwt", "token", "session", "oauth", "bearer"))
