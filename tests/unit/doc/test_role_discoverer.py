"""Unit tests for role_discoverer module (Phase 19)."""

from __future__ import annotations

from qaagent.doc.models import FeatureArea, RouteDoc
from qaagent.doc.role_discoverer import discover_roles


def _feature(fid: str, routes: list[RouteDoc], auth_required: bool = False) -> FeatureArea:
    return FeatureArea(id=fid, name=fid.title(), routes=routes, auth_required=auth_required)


def _route(path: str, method: str = "GET", auth_required: bool = False) -> RouteDoc:
    return RouteDoc(path=path, method=method, auth_required=auth_required)


class TestDiscoverRoles:
    def test_no_features_returns_unauthenticated(self):
        roles = discover_roles([])
        assert len(roles) == 1
        assert roles[0].id == "user-unauthenticated"

    def test_no_auth_routes_returns_unauthenticated(self):
        features = [_feature("products", [_route("/api/products")])]
        roles = discover_roles(features)
        assert len(roles) == 1
        assert roles[0].id == "user-unauthenticated"
        assert "products" in roles[0].associated_features

    def test_auth_routes_returns_user_role(self):
        features = [
            _feature("auth", [_route("/api/login", "POST"), _route("/api/register", "POST")]),
            _feature("products", [_route("/api/products")]),
        ]
        roles = discover_roles(features)
        role_ids = {r.id for r in roles}
        assert "user" in role_ids
        user_role = next(r for r in roles if r.id == "user")
        assert "auth" in user_role.associated_features
        assert "products" in user_role.associated_features

    def test_admin_routes_returns_admin_role(self):
        features = [
            _feature("auth", [_route("/api/login", "POST")]),
            _feature("admin", [_route("/admin/users"), _route("/admin/settings")]),
        ]
        roles = discover_roles(features)
        role_ids = {r.id for r in roles}
        assert "admin" in role_ids
        admin_role = next(r for r in roles if r.id == "admin")
        assert "manage" in admin_role.permissions

    def test_api_key_routes_returns_api_consumer(self):
        features = [
            _feature("api-keys", [_route("/api/api-key", "POST"), _route("/api/token", "POST")]),
        ]
        roles = discover_roles(features)
        role_ids = {r.id for r in roles}
        assert "api-consumer" in role_ids

    def test_auth_required_flag_infers_user_role(self):
        features = [_feature("dashboard", [_route("/dashboard")], auth_required=True)]
        roles = discover_roles(features)
        role_ids = {r.id for r in roles}
        assert "user" in role_ids

    def test_mixed_roles(self):
        features = [
            _feature("auth", [_route("/api/login", "POST")]),
            _feature("admin", [_route("/admin/panel")]),
            _feature("webhooks", [_route("/api/webhook", "POST")]),
            _feature("products", [_route("/api/products")]),
        ]
        roles = discover_roles(features)
        role_ids = {r.id for r in roles}
        assert "user" in role_ids
        assert "admin" in role_ids
        assert "api-consumer" in role_ids
        assert "user-unauthenticated" not in role_ids
