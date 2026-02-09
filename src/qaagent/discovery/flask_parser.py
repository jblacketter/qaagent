"""Flask route discovery via AST parsing."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base import FrameworkParser, RouteParam
from qaagent.analyzers.models import Route


# Default methods for Flask @app.route (if not specified)
_DEFAULT_METHODS = ["GET"]

# Auth decorator patterns
_AUTH_DECORATORS = {
    "login_required",
    "auth_required",
    "requires_auth",
    "jwt_required",
    "token_required",
    "permission_required",
    "roles_required",
    "admin_required",
}


class FlaskParser(FrameworkParser):
    """Discover routes from Flask source code using AST."""

    framework_name = "flask"

    def parse(self, source_dir: Path) -> List[Route]:
        routes: List[Route] = []
        # Collect Blueprint prefixes
        bp_prefixes = self._collect_blueprint_prefixes(source_dir)

        for py_file in self.find_route_files(source_dir):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue
            file_routes = self._parse_file(tree, py_file, source_dir, bp_prefixes)
            routes.extend(file_routes)

        return routes

    def find_route_files(self, source_dir: Path) -> List[Path]:
        candidates = []
        for py_file in sorted(source_dir.rglob("*.py")):
            rel = str(py_file.relative_to(source_dir))
            if any(skip in rel for skip in ("test_", "tests/", "venv/", ".venv/", "migrations/", "__pycache__")):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            if re.search(r"@\w+\.route\(", content):
                candidates.append(py_file)
        return candidates

    # ------------------------------------------------------------------

    def _collect_blueprint_prefixes(self, source_dir: Path) -> Dict[str, str]:
        """Collect Blueprint variable names and their url_prefix values."""
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
                # bp = Blueprint("name", __name__, url_prefix="/api")
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                        if self._call_name(node.value) == "Blueprint":
                            prefix = self._get_keyword_str(node.value, "url_prefix") or ""
                            prefixes[target.id] = prefix

                # app.register_blueprint(bp, url_prefix="/v1")
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    call = node.value
                    if self._is_attr_call(call, "register_blueprint") and call.args:
                        arg0 = call.args[0]
                        if isinstance(arg0, ast.Name) and arg0.id in prefixes:
                            extra = self._get_keyword_str(call, "url_prefix")
                            if extra is not None:
                                prefixes[arg0.id] = extra

        return prefixes

    def _parse_file(
        self,
        tree: ast.Module,
        py_file: Path,
        source_dir: Path,
        bp_prefixes: Dict[str, str],
    ) -> List[Route]:
        routes: List[Route] = []

        # Build map of variable name -> prefix for all blueprints/apps in this file
        var_prefixes: Dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    call_name = self._call_name(node.value)
                    if call_name == "Blueprint":
                        bp_name = target.id
                        prefix = bp_prefixes.get(bp_name, "")
                        if not prefix:
                            prefix = self._get_keyword_str(node.value, "url_prefix") or ""
                        var_prefixes[bp_name] = prefix
                    elif call_name == "Flask":
                        var_prefixes[target.id] = ""

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                result = self._parse_route_decorator(decorator)
                if result is None:
                    continue
                path, methods = result

                # Determine which variable owns this decorator
                route_var = self._get_decorator_var(decorator)
                prefix = var_prefixes.get(route_var, "") if route_var else ""

                full_path = prefix.rstrip("/") + "/" + path.lstrip("/") if path != "/" else prefix + path
                if not full_path.startswith("/"):
                    full_path = "/" + full_path

                # Extract params from Flask path converters: <int:id>, <name>
                path_params = self._extract_path_params(full_path)
                auth = self._detect_auth(node)

                params: Dict[str, list] = {}
                if path_params:
                    params["path"] = path_params

                metadata = {
                    "source": "flask",
                    "file": str(py_file.relative_to(source_dir)),
                    "function": node.name,
                }

                for method in methods:
                    route = self._normalize_route(
                        path=full_path,
                        method=method,
                        params=params,
                        auth_required=auth,
                        metadata=metadata,
                    )
                    routes.append(route)

        return routes

    @staticmethod
    def _get_decorator_var(decorator: ast.expr) -> Optional[str]:
        """Get the variable name from @var.route() decorator."""
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            val = decorator.func.value
            if isinstance(val, ast.Name):
                return val.id
        return None

    def _parse_route_decorator(self, decorator: ast.expr) -> Optional[Tuple[str, List[str]]]:
        """Parse @app.route("/path", methods=["GET", "POST"]).

        Returns (path, methods) or None.
        """
        if not isinstance(decorator, ast.Call):
            return None
        func = decorator.func
        if not isinstance(func, ast.Attribute) or func.attr != "route":
            return None

        # First positional arg is the path
        path = "/"
        if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
            path = decorator.args[0].value

        # methods keyword
        methods = list(_DEFAULT_METHODS)
        methods_node = self._get_keyword_node(decorator, "methods")
        if isinstance(methods_node, ast.List):
            extracted = []
            for elt in methods_node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    extracted.append(elt.value.upper())
            if extracted:
                methods = extracted

        return path, methods

    def _extract_path_params(self, path: str) -> List[RouteParam]:
        """Extract params from Flask-style path: /users/<int:id>."""
        params: List[RouteParam] = []
        # Match <type:name> or <name>
        for match in re.finditer(r"<(?:(\w+):)?(\w+)>", path):
            converter, name = match.group(1), match.group(2)
            type_map = {"int": "integer", "float": "number", "path": "string", "uuid": "uuid"}
            param_type = type_map.get(converter, "string") if converter else "string"
            params.append(RouteParam(name=name, type=param_type, required=True))
        return params

    def _detect_auth(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Detect auth decorators on route function."""
        for decorator in func_node.decorator_list:
            name = None
            if isinstance(decorator, ast.Name):
                name = decorator.id
            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                name = decorator.func.id
            elif isinstance(decorator, ast.Attribute):
                name = decorator.attr
            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                name = decorator.func.attr
            if name and name in _AUTH_DECORATORS:
                return True
        return False

    # ------------------------------------------------------------------
    # AST utilities
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
