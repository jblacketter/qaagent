"""Convert discovered CUJs into human-readable UserJourney objects."""

from __future__ import annotations

from typing import Dict, List

from .models import (
    DiscoveredCUJ,
    FeatureArea,
    JourneyStep,
    UserJourney,
)

# Map CUJ patterns to priority levels
_PATTERN_PRIORITY: Dict[str, str] = {
    "auth_flow": "high",
    "crud_lifecycle": "medium",
    "checkout_flow": "high",
    "onboarding_flow": "high",
    "search_browse": "medium",
}

# Human-readable expected outcomes per action keyword
_OUTCOME_MAP: Dict[str, str] = {
    "register": "Account is created and confirmation is shown",
    "sign up": "Account is created and confirmation is shown",
    "log in": "User is authenticated and redirected to dashboard",
    "log out": "Session is terminated and user is redirected to login",
    "access protected": "Protected content is displayed to authenticated user",
    "create": "New record is persisted and confirmation returned",
    "read": "Record data is retrieved and displayed",
    "update": "Record is modified and updated data returned",
    "delete": "Record is removed and confirmation returned",
    "browse": "List of items is displayed with pagination",
    "search": "Matching results are returned based on query",
    "view detail": "Full item details are displayed",
    "add item": "Item is added to cart with updated total",
    "proceed to checkout": "Order summary is displayed for review",
    "complete payment": "Payment is processed and order confirmation shown",
    "complete profile": "Profile information is saved",
    "configure settings": "User preferences are updated",
}


def _infer_outcome(action: str) -> str:
    """Infer an expected outcome from an action description."""
    action_lower = action.lower()
    for keyword, outcome in _OUTCOME_MAP.items():
        if keyword in action_lower:
            return outcome
    return "Action completes successfully"


def _infer_actor(cuj: DiscoveredCUJ) -> str:
    """Infer the actor (role) for a CUJ."""
    if cuj.pattern == "auth_flow":
        return "user"
    if cuj.pattern == "onboarding_flow":
        return "user"
    if cuj.pattern == "checkout_flow":
        return "user"
    # Check if any step involves auth-required routes
    has_auth_step = any(s.action and "protected" in s.action.lower() for s in cuj.steps)
    if has_auth_step:
        return "user"
    return "anonymous"


def build_user_journeys(
    cujs: List[DiscoveredCUJ],
    features: List[FeatureArea],
) -> List[UserJourney]:
    """Convert discovered CUJs into human-readable UserJourney objects.

    Each CUJ becomes a UserJourney with steps that include
    human-readable actions and expected outcomes.
    """
    feature_map = {f.id: f for f in features}
    journeys: List[UserJourney] = []

    for cuj in cujs:
        steps: List[JourneyStep] = []
        for cuj_step in cuj.steps:
            page_or_route = cuj_step.route
            if cuj_step.method and cuj_step.route:
                page_or_route = f"{cuj_step.method} {cuj_step.route}"

            steps.append(JourneyStep(
                order=cuj_step.order,
                action=cuj_step.action,
                page_or_route=page_or_route,
                expected_outcome=_infer_outcome(cuj_step.action),
            ))

        # Resolve feature names for the description
        feature_names = [
            feature_map[fid].name
            for fid in cuj.feature_ids
            if fid in feature_map
        ]

        description = cuj.description
        if feature_names and not description:
            description = f"User journey spanning {', '.join(feature_names)}."

        journeys.append(UserJourney(
            id=f"journey-{cuj.id}",
            name=cuj.name,
            description=description or cuj.name,
            actor=_infer_actor(cuj),
            steps=steps,
            feature_ids=cuj.feature_ids,
            priority=_PATTERN_PRIORITY.get(cuj.pattern, "medium"),
        ))

    return journeys
