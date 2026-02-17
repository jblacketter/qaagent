"""Unit tests for journey_builder module (Phase 19)."""

from __future__ import annotations

from qaagent.doc.models import CujStep, DiscoveredCUJ, FeatureArea, RouteDoc
from qaagent.doc.journey_builder import build_user_journeys


def _feature(fid: str) -> FeatureArea:
    return FeatureArea(id=fid, name=fid.title(), routes=[])


def _cuj(
    cuj_id: str,
    name: str,
    pattern: str,
    steps: list[CujStep],
    feature_ids: list[str] | None = None,
) -> DiscoveredCUJ:
    return DiscoveredCUJ(
        id=cuj_id, name=name, pattern=pattern, steps=steps,
        feature_ids=feature_ids or [],
    )


class TestBuildUserJourneys:
    def test_empty_cujs(self):
        journeys = build_user_journeys([], [])
        assert journeys == []

    def test_basic_conversion(self):
        cujs = [_cuj(
            "auth-flow", "Authentication Flow", "auth_flow",
            [
                CujStep(order=1, action="Log in with credentials", route="/api/login", method="POST"),
                CujStep(order=2, action="Access protected resource", route="/dashboard", method="GET"),
            ],
        )]
        journeys = build_user_journeys(cujs, [])
        assert len(journeys) == 1
        j = journeys[0]
        assert j.id == "journey-auth-flow"
        assert j.name == "Authentication Flow"
        assert j.priority == "high"  # auth_flow is high priority
        assert j.actor == "user"
        assert len(j.steps) == 2

    def test_steps_have_outcomes(self):
        cujs = [_cuj(
            "auth-flow", "Auth", "auth_flow",
            [CujStep(order=1, action="Log in with credentials", route="/login", method="POST")],
        )]
        journeys = build_user_journeys(cujs, [])
        step = journeys[0].steps[0]
        assert step.expected_outcome != ""
        assert "authenticated" in step.expected_outcome.lower()

    def test_page_or_route_combines_method_and_path(self):
        cujs = [_cuj(
            "crud-items", "Items CRUD", "crud_lifecycle",
            [CujStep(order=1, action="Create item", route="/api/items", method="POST")],
        )]
        journeys = build_user_journeys(cujs, [])
        assert journeys[0].steps[0].page_or_route == "POST /api/items"

    def test_feature_ids_propagated(self):
        features = [_feature("items")]
        cujs = [_cuj(
            "crud-items", "Items CRUD", "crud_lifecycle",
            [CujStep(order=1, action="Create item", route="/api/items", method="POST")],
            feature_ids=["items"],
        )]
        journeys = build_user_journeys(cujs, features)
        assert journeys[0].feature_ids == ["items"]

    def test_crud_lifecycle_priority(self):
        cujs = [_cuj(
            "crud-x", "X CRUD", "crud_lifecycle",
            [CujStep(order=1, action="Create x", route="/x", method="POST")],
        )]
        journeys = build_user_journeys(cujs, [])
        assert journeys[0].priority == "medium"

    def test_checkout_flow_priority(self):
        cujs = [_cuj(
            "checkout", "Checkout", "checkout_flow",
            [CujStep(order=1, action="Browse products", route="/products", method="GET")],
        )]
        journeys = build_user_journeys(cujs, [])
        assert journeys[0].priority == "high"

    def test_anonymous_actor_for_generic_cuj(self):
        cujs = [_cuj(
            "search", "Search", "search_browse",
            [CujStep(order=1, action="Search for items", route="/search", method="GET")],
        )]
        journeys = build_user_journeys(cujs, [])
        assert journeys[0].actor == "anonymous"
