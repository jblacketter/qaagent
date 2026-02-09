"""Django route discovery via AST + URL pattern parsing."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base import FrameworkParser, RouteParam
from qaagent.analyzers.models import Route


# DRF ViewSet standard actions
_VIEWSET_ACTIONS = {
    "list": ("GET", ""),
    "create": ("POST", ""),
    "retrieve": ("GET", "/{pk}"),
    "update": ("PUT", "/{pk}"),
    "partial_update": ("PATCH", "/{pk}"),
    "destroy": ("DELETE", "/{pk}"),
}

_AUTH_CLASSES = {
    "IsAuthenticated",
    "IsAdminUser",
    "IsAuthenticatedOrReadOnly",
    "DjangoModelPermissions",
    "DjangoObjectPermissions",
    "TokenAuthentication",
    "SessionAuthentication",
    "JWTAuthentication",
}

_AUTH_DECORATORS = {
    "login_required",
    "permission_required",
    "user_passes_test",
}


class DjangoParser(FrameworkParser):
    """Discover routes from Django source code."""

    framework_name = "django"

    def parse(self, source_dir: Path) -> List[Route]:
        routes: List[Route] = []

        # Phase 1: Parse urls.py files for URL patterns
        url_routes = self._parse_url_patterns(source_dir)
        routes.extend(url_routes)

        # Phase 2: Detect DRF ViewSets and router registrations
        drf_routes = self._parse_drf_viewsets(source_dir)
        routes.extend(drf_routes)

        return routes

    def find_route_files(self, source_dir: Path) -> List[Path]:
        """Find urls.py and views.py files."""
        candidates = []
        for py_file in sorted(source_dir.rglob("*.py")):
            rel = str(py_file.relative_to(source_dir))
            if any(skip in rel for skip in ("test_", "tests/", "venv/", ".venv/", "migrations/", "__pycache__")):
                continue
            if py_file.name in ("urls.py", "views.py", "viewsets.py", "routers.py"):
                candidates.append(py_file)
        return candidates

    # ------------------------------------------------------------------
    # URL pattern parsing
    # ------------------------------------------------------------------

    def _parse_url_patterns(self, source_dir: Path) -> List[Route]:
        """Parse urlpatterns from urls.py files."""
        routes: List[Route] = []

        for urls_file in sorted(source_dir.rglob("urls.py")):
            rel = str(urls_file.relative_to(source_dir))
            if any(skip in rel for skip in ("test_", "tests/", "venv/", ".venv/", "__pycache__")):
                continue
            try:
                source = urls_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            # Determine prefix from directory structure (e.g., myapp/urls.py typically included via include())
            prefix = self._infer_url_prefix(urls_file, source_dir, source)

            # Extract path() and re_path() calls from urlpatterns
            patterns = self._extract_patterns(source)
            for pattern_path, view_name, name in patterns:
                # Skip include() references (they just delegate)
                if view_name and "include" in view_name:
                    continue

                full_path = "/" + prefix.strip("/") + "/" + pattern_path.strip("/")
                full_path = re.sub(r"/+", "/", full_path)
                if not full_path.endswith("/") and full_path != "/":
                    full_path = full_path.rstrip("/")

                path_params = self._extract_path_params(full_path)
                params: Dict[str, list] = {}
                if path_params:
                    params["path"] = path_params

                # For URL patterns we don't know the method — default to GET
                # Class-based views handle multiple methods
                metadata = {
                    "source": "django",
                    "file": rel,
                    "view": view_name or "",
                    "url_name": name or "",
                }

                route = self._normalize_route(
                    path=full_path,
                    method="GET",
                    params=params,
                    auth_required=False,  # Can't determine from urls.py alone
                    metadata=metadata,
                    confidence=0.75,
                )
                routes.append(route)

        return routes

    def _extract_patterns(self, source: str) -> List[Tuple[str, Optional[str], Optional[str]]]:
        """Extract (path, view, name) tuples from urlpatterns source code.

        Handles:
        - path("api/users/", views.user_list, name="user-list")
        - path("api/users/<int:pk>/", views.user_detail)
        - re_path(r"^api/.*$", views.catch_all)
        """
        results: List[Tuple[str, Optional[str], Optional[str]]] = []

        # Match path() or re_path() calls
        pattern = re.compile(
            r'(?:path|re_path)\(\s*["\']([^"\']*)["\']'
            r'(?:\s*,\s*([^,\)]+))?'
            r'(?:\s*,\s*name\s*=\s*["\']([^"\']+)["\'])?',
            re.MULTILINE,
        )

        for match in pattern.finditer(source):
            url_path = match.group(1)
            view = match.group(2)
            name = match.group(3)

            if view:
                view = view.strip()
            results.append((url_path, view, name))

        return results

    def _infer_url_prefix(self, urls_file: Path, source_dir: Path, source: str) -> str:
        """Infer URL prefix from project structure.

        Root urls.py typically has no prefix. App urls.py are included
        via include() with a prefix in the parent.
        """
        # If this file is in the project root, no prefix
        rel = urls_file.relative_to(source_dir)
        if len(rel.parts) <= 1:
            return ""

        # The app name is typically the parent directory
        # But the actual prefix comes from the root urls.py include() call
        # We can't fully resolve this without running include() — use heuristic
        app_name = rel.parts[-2] if len(rel.parts) >= 2 else ""

        # Check if there's a common API prefix pattern
        if "api" in app_name.lower():
            return f"api"
        return ""

    def _extract_path_params(self, path: str) -> List[RouteParam]:
        """Extract params from Django path converters: <int:pk>, <slug:slug>."""
        params: List[RouteParam] = []
        type_map = {"int": "integer", "slug": "string", "uuid": "uuid", "str": "string", "path": "string"}

        for match in re.finditer(r"<(?:(\w+):)?(\w+)>", path):
            converter, name = match.group(1), match.group(2)
            param_type = type_map.get(converter, "string") if converter else "string"
            params.append(RouteParam(name=name, type=param_type, required=True))

        return params

    # ------------------------------------------------------------------
    # DRF ViewSet parsing
    # ------------------------------------------------------------------

    def _parse_drf_viewsets(self, source_dir: Path) -> List[Route]:
        """Detect DRF ViewSets and router.register() calls."""
        routes: List[Route] = []

        # Collect router registrations: router.register("prefix", ViewSetClass)
        registrations: List[Tuple[str, str, Path]] = []

        for py_file in sorted(source_dir.rglob("*.py")):
            rel = str(py_file.relative_to(source_dir))
            if any(skip in rel for skip in ("test_", "tests/", "venv/", ".venv/", "__pycache__")):
                continue
            try:
                src = py_file.read_text(encoding="utf-8")
                tree = ast.parse(src, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    call = node.value
                    if self._is_attr_call(call, "register") and len(call.args) >= 2:
                        prefix_arg = call.args[0]
                        viewset_arg = call.args[1]
                        if (
                            isinstance(prefix_arg, ast.Constant)
                            and isinstance(prefix_arg.value, str)
                            and isinstance(viewset_arg, ast.Name)
                        ):
                            registrations.append((prefix_arg.value, viewset_arg.id, py_file))

        # For each registration, try to find the ViewSet class and generate routes
        viewset_classes = self._collect_viewset_classes(source_dir)

        for prefix, viewset_name, reg_file in registrations:
            actions, custom_actions, auth = viewset_classes.get(viewset_name, (set(), [], False))

            for action_name in actions:
                if action_name in _VIEWSET_ACTIONS:
                    method, suffix = _VIEWSET_ACTIONS[action_name]
                    path = f"/{prefix.strip('/')}{suffix}"

                    path_params: List[RouteParam] = []
                    if "{pk}" in path:
                        path_params.append(RouteParam(name="pk", type="integer", required=True))

                    params: Dict[str, list] = {}
                    if path_params:
                        params["path"] = path_params

                    route = self._normalize_route(
                        path=path,
                        method=method,
                        params=params,
                        auth_required=auth,
                        metadata={
                            "source": "django-drf",
                            "viewset": viewset_name,
                            "action": action_name,
                        },
                        confidence=0.80,
                    )
                    routes.append(route)

            # Custom @action methods
            for action_method, action_path, detail in custom_actions:
                base = f"/{prefix.strip('/')}"
                if detail:
                    full_path = f"{base}/{{pk}}/{action_path}"
                else:
                    full_path = f"{base}/{action_path}"

                path_params = []
                if detail:
                    path_params.append(RouteParam(name="pk", type="integer", required=True))

                params_dict: Dict[str, list] = {}
                if path_params:
                    params_dict["path"] = path_params

                route = self._normalize_route(
                    path=full_path,
                    method=action_method,
                    params=params_dict,
                    auth_required=auth,
                    metadata={
                        "source": "django-drf",
                        "viewset": viewset_name,
                        "action": action_path,
                        "detail": detail,
                    },
                    confidence=0.80,
                )
                routes.append(route)

        return routes

    def _collect_viewset_classes(self, source_dir: Path) -> Dict[str, Tuple[set, list, bool]]:
        """Collect ViewSet classes: name -> (standard_actions, custom_actions, auth_required).

        Standard actions are inferred from base class (ModelViewSet -> all CRUD).
        Custom actions come from @action decorators.
        """
        viewsets: Dict[str, Tuple[set, list, bool]] = {}

        for py_file in sorted(source_dir.rglob("*.py")):
            rel = str(py_file.relative_to(source_dir))
            if any(skip in rel for skip in ("test_", "tests/", "venv/", ".venv/", "__pycache__")):
                continue
            try:
                src = py_file.read_text(encoding="utf-8")
                tree = ast.parse(src, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue

                base_names = {self._base_name(b) for b in node.bases}

                actions: set = set()
                if "ModelViewSet" in base_names:
                    actions = set(_VIEWSET_ACTIONS.keys())
                elif "ReadOnlyModelViewSet" in base_names:
                    actions = {"list", "retrieve"}
                elif "ViewSet" in base_names or "GenericViewSet" in base_names:
                    # Only explicitly defined methods
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if item.name in _VIEWSET_ACTIONS:
                                actions.add(item.name)

                if not actions and not any("ViewSet" in b for b in base_names):
                    continue

                # Check for auth
                auth = self._viewset_has_auth(node)

                # Collect @action decorators
                custom_actions: list = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for dec in item.decorator_list:
                            action_info = self._parse_action_decorator(dec, item.name)
                            if action_info:
                                custom_actions.append(action_info)

                viewsets[node.name] = (actions, custom_actions, auth)

        return viewsets

    def _viewset_has_auth(self, class_node: ast.ClassDef) -> bool:
        """Check if ViewSet has permission_classes with auth requirements."""
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "permission_classes":
                        if isinstance(item.value, (ast.List, ast.Tuple)):
                            for elt in item.value.elts:
                                name = self._base_name(elt)
                                if name in _AUTH_CLASSES:
                                    return True
        return False

    def _parse_action_decorator(self, decorator: ast.expr, func_name: str) -> Optional[Tuple[str, str, bool]]:
        """Parse @action(detail=True, methods=["post"]).

        Returns (method, url_path, detail) or None.
        """
        if not isinstance(decorator, ast.Call):
            return None
        func = decorator.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "action":
            return None

        # detail kwarg
        detail = False
        for kw in decorator.keywords:
            if kw.arg == "detail" and isinstance(kw.value, ast.Constant):
                detail = bool(kw.value.value)

        # methods kwarg
        methods = ["GET"]
        methods_node = None
        for kw in decorator.keywords:
            if kw.arg == "methods":
                methods_node = kw.value
        if isinstance(methods_node, ast.List):
            extracted = []
            for elt in methods_node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    extracted.append(elt.value.upper())
            if extracted:
                methods = extracted

        # url_path kwarg
        url_path = func_name.replace("_", "-")
        for kw in decorator.keywords:
            if kw.arg == "url_path" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                url_path = kw.value.value

        return methods[0], url_path, detail

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _base_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

    @staticmethod
    def _is_attr_call(call: ast.Call, attr_name: str) -> bool:
        return isinstance(call.func, ast.Attribute) and call.func.attr == attr_name
