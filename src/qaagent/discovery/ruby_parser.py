"""Ruby route discovery for Rails and Sinatra applications."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from qaagent.analyzers.models import Route

from .base import FrameworkParser, RouteParam

_HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
_SKIP_DIRS = {"vendor", ".bundle", "node_modules", ".git", "tmp", "log", "__pycache__"}


class RubyParser(FrameworkParser):
    """Discover routes from Ruby source files."""

    framework_name = "ruby"

    def parse(self, source_dir: Path) -> List[Route]:
        routes: List[Route] = []
        for rb_file in self.find_route_files(source_dir):
            try:
                content = rb_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = str(rb_file.relative_to(source_dir))
            if rb_file.name == "routes.rb" or "routes.draw" in content:
                routes.extend(self._parse_rails_routes(content, rel))
            else:
                routes.extend(self._parse_sinatra_routes(content, rel))
        return routes

    def find_route_files(self, source_dir: Path) -> List[Path]:
        candidates: List[Path] = []
        for rb_file in sorted(source_dir.rglob("*.rb")):
            rel = rb_file.relative_to(source_dir)
            if any(part in _SKIP_DIRS for part in rel.parts):
                continue
            if any(part in {"spec", "test", "tests"} for part in rel.parts):
                continue
            try:
                content = rb_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if rb_file.name == "routes.rb" or any(
                token in content
                for token in ("routes.draw", "resources :", "resource :", "get ", "post ", "Sinatra::Base")
            ):
                candidates.append(rb_file)
        return candidates

    def _parse_rails_routes(self, content: str, rel_file: str) -> List[Route]:
        routes: List[Route] = []
        prefix_stack: List[str] = []
        block_stack: List[bool] = []

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            pushed_prefix = False
            namespace_match = re.match(r"namespace\s+:([A-Za-z_]\w*)\s+do\b", line)
            if namespace_match:
                prefix_stack.append(f"/{namespace_match.group(1)}")
                block_stack.append(True)
                pushed_prefix = True
            else:
                scope_match = re.match(r"scope\s+[\"']([^\"']+)[\"']\s+do\b", line)
                if scope_match:
                    prefix_stack.append(scope_match.group(1))
                    block_stack.append(True)
                    pushed_prefix = True

            if not pushed_prefix and line.endswith(" do"):
                block_stack.append(False)

            current_prefix = self._stack_prefix(prefix_stack)

            verb_match = re.match(r"(get|post|put|patch|delete|head|options)\s+[\"']([^\"']+)[\"']", line)
            if verb_match:
                method = verb_match.group(1).upper()
                path = self._join_path(current_prefix, verb_match.group(2))
                routes.append(self._build_route(path=path, method=method, rel_file=rel_file, framework="rails", line=line))

            match_match = re.match(r"match\s+[\"']([^\"']+)[\"'].*\bvia:\s*(.+)$", line)
            if match_match:
                path = self._join_path(current_prefix, match_match.group(1))
                for method in self._extract_match_methods(match_match.group(2)):
                    routes.append(self._build_route(path=path, method=method, rel_file=rel_file, framework="rails", line=line))

            resources_match = re.match(r"resources\s+:([A-Za-z_]\w*)(.*)$", line)
            if resources_match:
                resource = resources_match.group(1)
                options = resources_match.group(2) or ""
                for method, resource_path in self._resource_routes(resource, singular=False, options=options):
                    full_path = self._join_path(current_prefix, resource_path)
                    routes.append(self._build_route(path=full_path, method=method, rel_file=rel_file, framework="rails", line=line))

            resource_match = re.match(r"resource\s+:([A-Za-z_]\w*)(.*)$", line)
            if resource_match:
                resource = resource_match.group(1)
                options = resource_match.group(2) or ""
                for method, resource_path in self._resource_routes(resource, singular=True, options=options):
                    full_path = self._join_path(current_prefix, resource_path)
                    routes.append(self._build_route(path=full_path, method=method, rel_file=rel_file, framework="rails", line=line))

            if line == "end" and block_stack:
                if block_stack.pop() and prefix_stack:
                    prefix_stack.pop()

        return routes

    def _parse_sinatra_routes(self, content: str, rel_file: str) -> List[Route]:
        routes: List[Route] = []
        lines = content.splitlines()
        for idx, raw_line in enumerate(lines):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"(get|post|put|patch|delete|head|options)\s+[\"']([^\"']+)[\"']", line)
            if not match:
                continue
            method = match.group(1).upper()
            path = self._normalize_path(match.group(2))
            window = "\n".join(lines[idx : idx + 5])
            route = self._normalize_route(
                path=path,
                method=method,
                params={"path": self._extract_path_params(path)} if self._extract_path_params(path) else {},
                auth_required=self._contains_auth(window),
                metadata={
                    "source": "ruby",
                    "framework": "sinatra",
                    "file": rel_file,
                },
                confidence=0.8,
            )
            routes.append(route)
        return routes

    def _build_route(self, *, path: str, method: str, rel_file: str, framework: str, line: str) -> Route:
        params = self._extract_path_params(path)
        return self._normalize_route(
            path=path,
            method=method,
            params={"path": params} if params else {},
            auth_required=self._contains_auth(line),
            metadata={
                "source": "ruby",
                "framework": framework,
                "file": rel_file,
            },
            confidence=0.85 if framework == "rails" else 0.8,
        )

    @staticmethod
    def _stack_prefix(parts: List[str]) -> str:
        cleaned = [p.strip("/") for p in parts if p and p.strip("/")]
        if not cleaned:
            return ""
        return "/" + "/".join(cleaned)

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
        return RubyParser._normalize_path(out)

    @staticmethod
    def _normalize_path(path: str) -> str:
        out = (path or "/").strip()
        out = re.sub(r"\*([A-Za-z_]\w*)", r"{\1}", out)
        out = re.sub(r"\*", "{wildcard}", out)
        out = re.sub(r"/+", "/", out)
        if not out.startswith("/"):
            out = "/" + out
        return out.rstrip("/") if out != "/" else out

    @staticmethod
    def _extract_match_methods(via_text: str) -> List[str]:
        methods = [m.upper() for m in re.findall(r":(get|post|put|patch|delete|head|options)", via_text, re.IGNORECASE)]
        if methods:
            return sorted(set(methods))
        any_match = re.search(r"\bany\b", via_text, re.IGNORECASE)
        return list(_HTTP_METHODS) if any_match else ["GET"]

    @staticmethod
    def _extract_only_actions(options: str) -> Optional[List[str]]:
        match = re.search(r"only:\s*\[([^\]]+)\]", options)
        if not match:
            return None
        actions = re.findall(r":([a-z_]+)", match.group(1))
        return actions or None

    def _resource_routes(self, name: str, *, singular: bool, options: str) -> List[tuple[str, str]]:
        only_actions = self._extract_only_actions(options)
        if singular:
            action_map = {
                "show": [("GET", f"/{name}")],
                "create": [("POST", f"/{name}")],
                "update": [("PUT", f"/{name}"), ("PATCH", f"/{name}")],
                "destroy": [("DELETE", f"/{name}")],
            }
            default = ["show", "create", "update", "destroy"]
        else:
            action_map = {
                "index": [("GET", f"/{name}")],
                "create": [("POST", f"/{name}")],
                "show": [("GET", f"/{name}/:id")],
                "update": [("PUT", f"/{name}/:id"), ("PATCH", f"/{name}/:id")],
                "destroy": [("DELETE", f"/{name}/:id")],
            }
            default = ["index", "create", "show", "update", "destroy"]

        selected = only_actions or default
        routes: List[tuple[str, str]] = []
        for action in selected:
            routes.extend(action_map.get(action, []))
        return routes

    @staticmethod
    def _extract_path_params(path: str) -> List[RouteParam]:
        names = set(re.findall(r":([A-Za-z_]\w*)", path))
        names.update(re.findall(r"\{([A-Za-z_]\w*)\}", path))
        return [RouteParam(name=name, type="string", required=True) for name in sorted(names)]

    @staticmethod
    def _contains_auth(text: str) -> bool:
        lowered = text.lower()
        return any(token in lowered for token in ("authenticate", "authorize", "current_user", "jwt", "token"))
