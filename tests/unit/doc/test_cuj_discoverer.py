"""Tests for CUJ auto-discovery."""

import pytest
from qaagent.doc.cuj_discoverer import discover_cujs, to_cuj_config
from qaagent.doc.models import FeatureArea, RouteDoc


def _make_feature(id, name, routes=None, crud_ops=None):
    return FeatureArea(
        id=id,
        name=name,
        routes=routes or [],
        crud_operations=crud_ops or [],
    )


def _make_route(path, method="GET", auth=False, summary=None):
    return RouteDoc(path=path, method=method, auth_required=auth, summary=summary)


class TestAuthFlowDetection:
    def test_detects_login(self):
        features = [_make_feature("auth", "Auth", routes=[
            _make_route("/api/login", "POST"),
        ])]
        cujs = discover_cujs(features)
        auth_cuj = next((c for c in cujs if c.pattern == "auth_flow"), None)
        assert auth_cuj is not None
        assert any(s.action == "Log in with credentials" for s in auth_cuj.steps)

    def test_detects_full_auth_flow(self):
        features = [_make_feature("auth", "Auth", routes=[
            _make_route("/api/register", "POST"),
            _make_route("/api/login", "POST"),
            _make_route("/api/logout", "POST"),
            _make_route("/api/dashboard", "GET", auth=True),
        ])]
        cujs = discover_cujs(features)
        auth_cuj = next((c for c in cujs if c.pattern == "auth_flow"), None)
        assert auth_cuj is not None
        assert len(auth_cuj.steps) == 4  # register, login, access protected, logout
        assert auth_cuj.confidence == 0.9

    def test_no_auth_without_login(self):
        features = [_make_feature("public", "Public", routes=[
            _make_route("/api/about", "GET"),
        ])]
        cujs = discover_cujs(features)
        assert not any(c.pattern == "auth_flow" for c in cujs)

    def test_partial_auth_flow(self):
        features = [_make_feature("auth", "Auth", routes=[
            _make_route("/api/login", "POST"),
            _make_route("/api/dashboard", "GET", auth=True),
        ])]
        cujs = discover_cujs(features)
        auth_cuj = next((c for c in cujs if c.pattern == "auth_flow"), None)
        assert auth_cuj is not None
        assert auth_cuj.confidence == 0.7  # no register or logout


class TestCrudLifecycleDetection:
    def test_detects_full_crud(self):
        features = [_make_feature("users", "Users",
            routes=[
                _make_route("/users", "GET"),
                _make_route("/users", "POST"),
                _make_route("/users/{id}", "PUT"),
                _make_route("/users/{id}", "DELETE"),
            ],
            crud_ops=["create", "read", "update", "delete"],
        )]
        cujs = discover_cujs(features)
        crud_cuj = next((c for c in cujs if c.pattern == "crud_lifecycle"), None)
        assert crud_cuj is not None
        assert crud_cuj.id == "crud-users"
        assert len(crud_cuj.steps) == 4
        assert crud_cuj.confidence == 0.95

    def test_no_crud_for_partial(self):
        features = [_make_feature("users", "Users",
            routes=[
                _make_route("/users", "GET"),
                _make_route("/users", "POST"),
            ],
            crud_ops=["create", "read"],
        )]
        cujs = discover_cujs(features)
        assert not any(c.pattern == "crud_lifecycle" for c in cujs)

    def test_multiple_crud_features(self):
        features = [
            _make_feature("users", "Users",
                routes=[
                    _make_route("/users", "GET"),
                    _make_route("/users", "POST"),
                    _make_route("/users/{id}", "PUT"),
                    _make_route("/users/{id}", "DELETE"),
                ],
                crud_ops=["create", "read", "update", "delete"],
            ),
            _make_feature("orders", "Orders",
                routes=[
                    _make_route("/orders", "GET"),
                    _make_route("/orders", "POST"),
                    _make_route("/orders/{id}", "PATCH"),
                    _make_route("/orders/{id}", "DELETE"),
                ],
                crud_ops=["create", "read", "update", "delete"],
            ),
        ]
        cujs = discover_cujs(features)
        crud_cujs = [c for c in cujs if c.pattern == "crud_lifecycle"]
        assert len(crud_cujs) == 2


class TestCheckoutFlowDetection:
    def test_detects_checkout(self):
        features = [_make_feature("shop", "Shop", routes=[
            _make_route("/products", "GET"),
            _make_route("/cart", "POST"),
            _make_route("/checkout", "POST"),
            _make_route("/payment", "POST"),
        ])]
        cujs = discover_cujs(features)
        checkout = next((c for c in cujs if c.pattern == "checkout_flow"), None)
        assert checkout is not None
        assert len(checkout.steps) == 4

    def test_no_checkout_without_cart_or_payment(self):
        features = [_make_feature("public", "Public", routes=[
            _make_route("/products", "GET"),
            _make_route("/about", "GET"),
        ])]
        cujs = discover_cujs(features)
        assert not any(c.pattern == "checkout_flow" for c in cujs)


class TestOnboardingFlowDetection:
    def test_detects_onboarding(self):
        features = [_make_feature("user", "User", routes=[
            _make_route("/register", "POST"),
            _make_route("/profile", "PUT"),
            _make_route("/settings", "PATCH"),
        ])]
        cujs = discover_cujs(features)
        onboarding = next((c for c in cujs if c.pattern == "onboarding_flow"), None)
        assert onboarding is not None
        assert len(onboarding.steps) == 3

    def test_no_onboarding_without_signup(self):
        features = [_make_feature("user", "User", routes=[
            _make_route("/profile", "PUT"),
            _make_route("/settings", "PATCH"),
        ])]
        cujs = discover_cujs(features)
        assert not any(c.pattern == "onboarding_flow" for c in cujs)


class TestSearchFlowDetection:
    def test_detects_search(self):
        features = [_make_feature("catalog", "Catalog", routes=[
            _make_route("/search", "GET"),
            _make_route("/items/{id}", "GET"),
        ])]
        cujs = discover_cujs(features)
        search = next((c for c in cujs if c.pattern == "search_browse"), None)
        assert search is not None
        assert len(search.steps) == 2

    def test_no_search_without_endpoints(self):
        features = [_make_feature("internal", "Internal", routes=[
            _make_route("/admin/config", "PUT"),
        ])]
        cujs = discover_cujs(features)
        assert not any(c.pattern == "search_browse" for c in cujs)


class TestSortingByConfidence:
    def test_sorted_by_confidence(self):
        features = [_make_feature("app", "App", routes=[
            _make_route("/users", "GET"),
            _make_route("/users", "POST"),
            _make_route("/users/{id}", "PUT"),
            _make_route("/users/{id}", "DELETE"),
            _make_route("/login", "POST"),
            _make_route("/register", "POST"),
            _make_route("/logout", "POST"),
            _make_route("/dashboard", "GET", auth=True),
        ], crud_ops=["create", "read", "update", "delete"])]
        cujs = discover_cujs(features)
        assert len(cujs) >= 2
        # Verify sorted by confidence descending
        for i in range(len(cujs) - 1):
            assert cujs[i].confidence >= cujs[i + 1].confidence


class TestToCujConfig:
    def test_converts_to_cuj_config(self):
        discovered = [
            discover_cujs([_make_feature("auth", "Auth", routes=[
                _make_route("/login", "POST"),
                _make_route("/dashboard", "GET", auth=True),
            ])])[0],
        ]
        config = to_cuj_config(discovered, product_name="Test App")
        assert config.product == "Test App"
        assert len(config.journeys) == 1
        journey = config.journeys[0]
        assert journey.id == "auth-flow"
        assert journey.name == "Authentication Flow"
        assert len(journey.apis) > 0
        assert journey.apis[0]["method"] == "POST"
        assert journey.apis[0]["endpoint"] == "/login"

    def test_empty_discovered(self):
        config = to_cuj_config([])
        assert config.journeys == []

    def test_acceptance_criteria(self):
        features = [_make_feature("users", "Users",
            routes=[
                _make_route("/users", "GET"),
                _make_route("/users", "POST"),
                _make_route("/users/{id}", "PUT"),
                _make_route("/users/{id}", "DELETE"),
            ],
            crud_ops=["create", "read", "update", "delete"],
        )]
        discovered = discover_cujs(features)
        config = to_cuj_config(discovered)
        crud_journey = next(j for j in config.journeys if j.id == "crud-users")
        assert len(crud_journey.acceptance) == 4
        assert crud_journey.acceptance[0].startswith("Step 1:")
