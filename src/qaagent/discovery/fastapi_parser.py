"""FastAPI route discovery via AST parsing."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .base import FrameworkParser, RouteParam
from qaagent.analyzers.models import Route


# HTTP methods exposed by FastAPI decorators
_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# Common auth dependency patterns
_AUTH_PATTERNS = {
    "get_current_user",
    "get_current_active_user",
    "current_user",
    "require_auth",
    "HTTPBearer",
    "HTTPBasic",
    "OAuth2PasswordBearer",
    "Security",
}


class FastAPIParser(FrameworkParser):
    """Discover routes from FastAPI source code using AST."""

    framework_name = "fastapi"

    def parse(self, source_dir: Path) -> List[Route]:
        routes: List[Route] = []
        # First pass: collect router prefixes from include_router() calls
        router_prefixes = self._collect_router_prefixes(source_dir)

        for py_file in self.find_route_files(source_dir):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            file_routes = self._parse_file(tree, source, py_file, source_dir, router_prefixes)
            routes.extend(file_routes)

        return routes

    def find_route_files(self, source_dir: Path) -> List[Path]:
        """Find Python files that may contain FastAPI route definitions."""
        candidates = []
        for py_file in sorted(source_dir.rglob("*.py")):
            # Skip test files, migrations, venvs
            rel = str(py_file.relative_to(source_dir))
            if any(skip in rel for skip in ("test_", "tests/", "venv/", ".venv/", "migrations/", "__pycache__")):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            # Quick check for FastAPI decorator patterns
            if re.search(r"@\w+\.(get|post|put|patch|delete|head|options)\(", content):
                candidates.append(py_file)
        return candidates

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_router_prefixes(self, source_dir: Path) -> Dict[str, str]:
        """Scan for APIRouter(prefix=...) and include_router(..., prefix=...) calls.

        Returns a mapping of router variable name -> accumulated prefix.
        """
        prefixes: Dict[str, str] = {}

        for py_file in sorted(source_dir.rglob("*.py")):
            rel = str(py_file.relative_to(source_dir))
            if any(skip in rel for skip in ("test_", "tests/", "venv/", ".venv/", "__pycache__")):
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                # router = APIRouter(prefix="/api/v1")
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                        func = node.value
                        if self._call_name(func) == "APIRouter":
                            prefix = self._get_keyword_str(func, "prefix") or ""
                            prefixes[target.id] = prefix

                # app.include_router(some_router, prefix="/items")
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    call = node.value
                    if self._is_attr_call(call, "include_router") and call.args:
                        arg0 = call.args[0]
                        if isinstance(arg0, ast.Name) and arg0.id in prefixes:
                            extra = self._get_keyword_str(call, "prefix") or ""
                            prefixes[arg0.id] = extra + prefixes[arg0.id]

        return prefixes

    def _parse_file(
        self,
        tree: ast.Module,
        source: str,
        py_file: Path,
        source_dir: Path,
        router_prefixes: Dict[str, str],
    ) -> List[Route]:
        routes: List[Route] = []

        # Build map of variable name -> prefix for all routers in this file
        var_prefixes: Dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    if self._call_name(node.value) == "APIRouter":
                        prefix = self._get_keyword_str(node.value, "prefix") or ""
                        # Check if this router has accumulated prefix from include_router
                        accumulated = router_prefixes.get(target.id, "")
                        if accumulated:
                            prefix = accumulated
                        var_prefixes[target.id] = prefix

        # Walk for decorated async/sync function definitions
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                method, path = self._parse_route_decorator(decorator)
                if method is None:
                    continue

                # Determine which router variable owns this decorator
                router_var = self._get_decorator_var(decorator)
                prefix = var_prefixes.get(router_var, "") if router_var else ""

                full_path = prefix.rstrip("/") + "/" + path.lstrip("/") if path else prefix or "/"
                if not full_path.startswith("/"):
                    full_path = "/" + full_path

                # Extract params from function signature
                path_params, query_params = self._extract_params(node, full_path)
                auth = self._detect_auth(node, source)
                tags = self._extract_tags(decorator)
                response_model = self._extract_response_model(decorator)

                params: Dict[str, list] = {}
                if path_params:
                    params["path"] = path_params
                if query_params:
                    params["query"] = query_params

                metadata = {
                    "source": "fastapi",
                    "file": str(py_file.relative_to(source_dir)),
                    "function": node.name,
                }
                if response_model:
                    metadata["response_model"] = response_model

                route = self._normalize_route(
                    path=full_path,
                    method=method,
                    params=params,
                    auth_required=auth,
                    tags=tags or None,
                    metadata=metadata,
                )
                routes.append(route)

        return routes

    @staticmethod
    def _get_decorator_var(decorator: ast.Call) -> Optional[str]:
        """Get the variable name from @var.method() decorator."""
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            val = decorator.func.value
            if isinstance(val, ast.Name):
                return val.id
        return None

    def _parse_route_decorator(self, decorator: ast.expr) -> Tuple[Optional[str], Optional[str]]:
        """Parse @app.get("/path") or @router.post("/path") decorators.

        Returns (method, path) or (None, None).
        """
        if not isinstance(decorator, ast.Call):
            return None, None
        func = decorator.func
        if not isinstance(func, ast.Attribute):
            return None, None
        method_name = func.attr
        if method_name not in _HTTP_METHODS:
            return None, None

        # First positional arg is the path
        path = "/"
        if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
            path = decorator.args[0].value

        return method_name.upper(), path

    def _extract_params(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef, path: str
    ) -> Tuple[List[RouteParam], List[RouteParam]]:
        """Extract path and query params from function signature."""
        path_param_names = set(re.findall(r"\{(\w+)\}", path))
        path_params: List[RouteParam] = []
        query_params: List[RouteParam] = []

        for arg in func_node.args.args:
            name = arg.arg
            if name in ("self", "cls", "request", "response", "db", "session"):
                continue

            # Resolve type hint
            param_type = "string"
            if arg.annotation:
                param_type = self._resolve_type(arg.annotation)

            if name in path_param_names:
                path_params.append(RouteParam(name=name, type=param_type, required=True))
            else:
                # Skip Depends() and other DI params
                if param_type in ("Depends", "Security", "Body", "Header", "Cookie"):
                    continue
                query_params.append(RouteParam(name=name, type=param_type, required=False))

        return path_params, query_params

    def _detect_auth(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef, source: str) -> bool:
        """Detect if a function requires authentication via Depends() or decorators."""
        for arg in func_node.args.args:
            if arg.annotation and self._annotation_matches_auth(arg.annotation):
                return True
        # Check defaults for Depends(get_current_user)
        for default in func_node.args.defaults:
            if isinstance(default, ast.Call) and self._call_name(default) in ("Depends", "Security"):
                if default.args and isinstance(default.args[0], ast.Name):
                    if default.args[0].id in _AUTH_PATTERNS:
                        return True
        return False

    def _annotation_matches_auth(self, annotation: ast.expr) -> bool:
        """Check if a type annotation references an auth type."""
        if isinstance(annotation, ast.Name) and annotation.id in _AUTH_PATTERNS:
            return True
        if isinstance(annotation, ast.Subscript):
            return self._annotation_matches_auth(annotation.value)
        return False

    def _extract_tags(self, decorator: ast.Call) -> Optional[List[str]]:
        """Extract tags=["..."] from route decorator."""
        val = self._get_keyword_node(decorator, "tags")
        if isinstance(val, ast.List):
            tags = []
            for elt in val.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    tags.append(elt.value)
            return tags or None
        return None

    def _extract_response_model(self, decorator: ast.Call) -> Optional[str]:
        """Extract response_model=SomeModel from decorator."""
        val = self._get_keyword_node(decorator, "response_model")
        if isinstance(val, ast.Name):
            return val.id
        return None

    # ------------------------------------------------------------------
    # AST utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _call_name(call: ast.Call) -> Optional[str]:
        if isinstance(call.func, ast.Name):
            return call.func.id
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        return None

    @staticmethod
    def _is_attr_call(call: ast.Call, attr_name: str) -> bool:
        return isinstance(call.func, ast.Attribute) and call.func.attr == attr_name

    @staticmethod
    def _get_keyword_str(call: ast.Call, keyword: str) -> Optional[str]:
        for kw in call.keywords:
            if kw.arg == keyword and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
        return None

    @staticmethod
    def _get_keyword_node(call: ast.Call, keyword: str) -> Optional[ast.expr]:
        for kw in call.keywords:
            if kw.arg == keyword:
                return kw.value
        return None

    @staticmethod
    def _resolve_type(annotation: ast.expr) -> str:
        if isinstance(annotation, ast.Name):
            type_map = {"int": "integer", "float": "number", "str": "string", "bool": "boolean"}
            return type_map.get(annotation.id, annotation.id)
        if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
            return annotation.value
        if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
            return annotation.value.id  # e.g. Optional, List
        return "string"
