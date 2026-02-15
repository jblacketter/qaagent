"""Tests for feature grouping logic."""

import pytest
from qaagent.analyzers.models import Route, RouteSource
from qaagent.doc.feature_grouper import group_routes, _extract_prefix, _slugify


class TestExtractPrefix:
    def test_simple_path(self):
        assert _extract_prefix("/users") == "users"

    def test_nested_path(self):
        assert _extract_prefix("/users/{id}") == "users"

    def test_api_prefix(self):
        assert _extract_prefix("/api/users") == "users"

    def test_versioned_prefix(self):
        assert _extract_prefix("/api/v1/users") == "users"

    def test_deep_path(self):
        assert _extract_prefix("/api/v2/orders/{id}/items") == "orders"

    def test_root_path(self):
        assert _extract_prefix("/") == "root"

    def test_only_param(self):
        assert _extract_prefix("/{id}") == "root"

    def test_health_check(self):
        assert _extract_prefix("/health") == "health"

    def test_high_version_number(self):
        assert _extract_prefix("/api/v10/users") == "users"

    def test_v4_prefix(self):
        assert _extract_prefix("/api/v4/orders/{id}") == "orders"


class TestSlugify:
    def test_simple(self):
        assert _slugify("Users") == "users"

    def test_spaces(self):
        assert _slugify("User Profiles") == "user-profiles"

    def test_special_chars(self):
        assert _slugify("users/admin!") == "users-admin"

    def test_empty(self):
        assert _slugify("") == "unknown"


class TestGroupRoutes:
    def _make_route(self, path, method="GET", tags=None, auth=False, summary=None):
        return Route(
            path=path,
            method=method,
            auth_required=auth,
            tags=tags or [],
            summary=summary,
            source=RouteSource.OPENAPI,
        )

    def test_empty_routes(self):
        features = group_routes([])
        assert features == []

    def test_group_by_tag(self):
        routes = [
            self._make_route("/users", "GET", tags=["users"]),
            self._make_route("/users", "POST", tags=["users"]),
            self._make_route("/orders", "GET", tags=["orders"]),
        ]
        features = group_routes(routes)
        assert len(features) == 2

        names = {f.name for f in features}
        assert "Orders" in names
        assert "Users" in names

        user_feature = next(f for f in features if f.id == "users")
        assert len(user_feature.routes) == 2

    def test_group_by_prefix_when_no_tags(self):
        routes = [
            self._make_route("/api/v1/users", "GET"),
            self._make_route("/api/v1/users/{id}", "GET"),
            self._make_route("/api/v1/users", "POST"),
            self._make_route("/api/v1/orders", "GET"),
        ]
        features = group_routes(routes)
        assert len(features) == 2

        user_feature = next(f for f in features if f.id == "users")
        assert len(user_feature.routes) == 3

        order_feature = next(f for f in features if f.id == "orders")
        assert len(order_feature.routes) == 1

    def test_mixed_tagged_and_untagged(self):
        routes = [
            self._make_route("/users", "GET", tags=["users"]),
            self._make_route("/health", "GET"),  # no tag
        ]
        features = group_routes(routes)
        assert len(features) == 2

    def test_crud_detection(self):
        routes = [
            self._make_route("/items", "GET", tags=["items"]),
            self._make_route("/items", "POST", tags=["items"]),
            self._make_route("/items/{id}", "PUT", tags=["items"]),
            self._make_route("/items/{id}", "DELETE", tags=["items"]),
        ]
        features = group_routes(routes)
        assert len(features) == 1
        feature = features[0]
        assert feature.has_full_crud
        assert sorted(feature.crud_operations) == ["create", "delete", "read", "update"]

    def test_auth_aggregation(self):
        routes = [
            self._make_route("/admin/users", "GET", tags=["admin"], auth=True),
            self._make_route("/admin/settings", "GET", tags=["admin"], auth=False),
        ]
        features = group_routes(routes)
        assert features[0].auth_required is True  # any route with auth → feature auth

    def test_all_public(self):
        routes = [
            self._make_route("/public/docs", "GET", tags=["public"]),
            self._make_route("/public/about", "GET", tags=["public"]),
        ]
        features = group_routes(routes)
        assert features[0].auth_required is False

    def test_tag_aggregation(self):
        routes = [
            self._make_route("/users", "GET", tags=["users", "v1"]),
            self._make_route("/users", "POST", tags=["users", "v2"]),
        ]
        features = group_routes(routes)
        user_feature = features[0]
        # Both tags should be collected
        assert "v1" in user_feature.tags
        assert "v2" in user_feature.tags
        assert "users" in user_feature.tags

    def test_feature_name_formatting(self):
        routes = [
            self._make_route("/user-profiles", "GET"),
        ]
        features = group_routes(routes)
        assert features[0].name == "User Profiles"

    def test_deterministic_order(self):
        routes = [
            self._make_route("/z-feature", "GET", tags=["z-feature"]),
            self._make_route("/a-feature", "GET", tags=["a-feature"]),
        ]
        features = group_routes(routes)
        assert features[0].id == "a-feature"
        assert features[1].id == "z-feature"

    def test_merges_tagged_and_untagged_with_same_slug(self):
        """Tagged and untagged routes with the same slug should merge into one feature."""
        routes = [
            self._make_route("/users", "GET", tags=["users"]),
            self._make_route("/users/{id}", "POST", tags=[]),
        ]
        features = group_routes(routes)
        assert len(features) == 1
        assert features[0].id == "users"
        assert len(features[0].routes) == 2

    def test_no_duplicate_feature_ids(self):
        """Ensure no duplicate feature IDs when tagged and prefix groups collide."""
        routes = [
            self._make_route("/users", "GET", tags=["users"]),
            self._make_route("/users", "POST", tags=["users"]),
            self._make_route("/users/{id}", "GET", tags=[]),
            self._make_route("/users/{id}", "DELETE", tags=[]),
        ]
        features = group_routes(routes)
        ids = [f.id for f in features]
        assert len(ids) == len(set(ids)), f"Duplicate feature IDs found: {ids}"
        assert "users" in ids
        users = [f for f in features if f.id == "users"][0]
        assert len(users.routes) == 4
