"""CUJ auto-discovery from route analysis.

Detects common user journey patterns:
1. Auth Flow — login/register/logout routes
2. CRUD Lifecycle — feature areas with all 4 CRUD operations
3. Checkout/Payment — cart + payment routes
4. Onboarding — registration + profile + settings routes
5. Search/Browse — search + detail endpoints
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from ..analyzers.cuj_config import CUJ, CUJConfig
from .models import CujStep, DiscoveredCUJ, FeatureArea, RouteDoc


@dataclass
class _RouteIndex:
    """Indexed view of routes for pattern matching."""

    by_path_keyword: Dict[str, List[RouteDoc]] = field(default_factory=dict)
    all_routes: List[RouteDoc] = field(default_factory=list)

    @classmethod
    def build(cls, features: List[FeatureArea]) -> "_RouteIndex":
        idx = cls()
        for feature in features:
            for route in feature.routes:
                idx.all_routes.append(route)
                # Index by meaningful path keywords
                path_lower = route.path.lower()
                for keyword in _extract_keywords(path_lower):
                    idx.by_path_keyword.setdefault(keyword, []).append(route)
        return idx


def _extract_keywords(path: str) -> List[str]:
    """Extract meaningful keywords from a path."""
    segments = path.strip("/").split("/")
    keywords = []
    for seg in segments:
        if seg.startswith("{") or seg == "api" or re.fullmatch(r"v\d+", seg):
            continue
        # Split on hyphens/underscores too
        for part in re.split(r"[-_]", seg):
            if part and len(part) > 1:
                keywords.append(part.lower())
    return keywords


def _find_route(index: _RouteIndex, keywords: List[str], method: Optional[str] = None) -> Optional[RouteDoc]:
    """Find a route matching any of the keywords and optionally a method."""
    for kw in keywords:
        for route in index.by_path_keyword.get(kw, []):
            if method is None or route.method.upper() == method.upper():
                return route
    return None


def _detect_auth_flow(index: _RouteIndex) -> Optional[DiscoveredCUJ]:
    """Detect auth flow: register → login → access protected → logout."""
    register = _find_route(index, ["register", "signup", "sign"], "POST")
    login = _find_route(index, ["login", "signin", "authenticate"], "POST")
    logout = _find_route(index, ["logout", "signout"], "POST") or _find_route(index, ["logout", "signout"], "DELETE")

    if not login:
        return None

    steps: list[CujStep] = []
    order = 1

    if register:
        steps.append(CujStep(order=order, action="Register new account", route=register.path, method=register.method))
        order += 1

    steps.append(CujStep(order=order, action="Log in with credentials", route=login.path, method=login.method))
    order += 1

    # Find a protected route
    protected = next((r for r in index.all_routes if r.auth_required and r.method == "GET"), None)
    if protected:
        steps.append(CujStep(order=order, action="Access protected resource", route=protected.path, method=protected.method))
        order += 1

    if logout:
        steps.append(CujStep(order=order, action="Log out", route=logout.path, method=logout.method))

    confidence = 0.9 if register and logout else 0.7

    return DiscoveredCUJ(
        id="auth-flow",
        name="Authentication Flow",
        description="User registration, login, and logout journey.",
        pattern="auth_flow",
        steps=steps,
        confidence=confidence,
    )


def _detect_crud_lifecycle(features: List[FeatureArea]) -> List[DiscoveredCUJ]:
    """Detect CRUD lifecycles for feature areas with all 4 operations."""
    cujs: list[DiscoveredCUJ] = []

    for feature in features:
        if not feature.has_full_crud:
            continue

        # Find routes for each CRUD operation
        create_route = next((r for r in feature.routes if r.method in ("POST",)), None)
        read_route = next((r for r in feature.routes if r.method == "GET"), None)
        update_route = next((r for r in feature.routes if r.method in ("PUT", "PATCH")), None)
        delete_route = next((r for r in feature.routes if r.method == "DELETE"), None)

        steps: list[CujStep] = []
        order = 1

        if create_route:
            steps.append(CujStep(order=order, action=f"Create {feature.name.lower()}", route=create_route.path, method=create_route.method))
            order += 1
        if read_route:
            steps.append(CujStep(order=order, action=f"Read {feature.name.lower()}", route=read_route.path, method=read_route.method))
            order += 1
        if update_route:
            steps.append(CujStep(order=order, action=f"Update {feature.name.lower()}", route=update_route.path, method=update_route.method))
            order += 1
        if delete_route:
            steps.append(CujStep(order=order, action=f"Delete {feature.name.lower()}", route=delete_route.path, method=delete_route.method))

        cujs.append(DiscoveredCUJ(
            id=f"crud-{feature.id}",
            name=f"{feature.name} CRUD Lifecycle",
            description=f"Full create-read-update-delete lifecycle for {feature.name.lower()}.",
            pattern="crud_lifecycle",
            steps=steps,
            feature_ids=[feature.id],
            confidence=0.95,
        ))

    return cujs


def _detect_checkout_flow(index: _RouteIndex) -> Optional[DiscoveredCUJ]:
    """Detect checkout/payment flow: browse → add to cart → checkout → pay."""
    cart_add = _find_route(index, ["cart", "basket"], "POST")
    checkout = _find_route(index, ["checkout", "order"], "POST")
    payment = _find_route(index, ["payment", "pay", "charge", "stripe"], "POST")
    browse = _find_route(index, ["products", "items", "catalog", "shop"], "GET")

    if not (cart_add or checkout or payment):
        return None

    steps: list[CujStep] = []
    order = 1

    if browse:
        steps.append(CujStep(order=order, action="Browse products", route=browse.path, method=browse.method))
        order += 1

    if cart_add:
        steps.append(CujStep(order=order, action="Add item to cart", route=cart_add.path, method=cart_add.method))
        order += 1

    if checkout:
        steps.append(CujStep(order=order, action="Proceed to checkout", route=checkout.path, method=checkout.method))
        order += 1

    if payment:
        steps.append(CujStep(order=order, action="Complete payment", route=payment.path, method=payment.method))

    if len(steps) < 2:
        return None

    return DiscoveredCUJ(
        id="checkout-flow",
        name="Checkout Flow",
        description="Product browsing through payment completion.",
        pattern="checkout_flow",
        steps=steps,
        confidence=0.8,
    )


def _detect_onboarding_flow(index: _RouteIndex) -> Optional[DiscoveredCUJ]:
    """Detect onboarding: sign up → complete profile → configure settings."""
    signup = _find_route(index, ["register", "signup"], "POST")
    profile = _find_route(index, ["profile", "account"], "PUT") or _find_route(index, ["profile", "account"], "PATCH")
    settings = _find_route(index, ["settings", "preferences", "config"], "PUT") or \
               _find_route(index, ["settings", "preferences", "config"], "PATCH")

    if not (signup and (profile or settings)):
        return None

    steps: list[CujStep] = []
    order = 1

    steps.append(CujStep(order=order, action="Sign up for account", route=signup.path, method=signup.method))
    order += 1

    if profile:
        steps.append(CujStep(order=order, action="Complete profile", route=profile.path, method=profile.method))
        order += 1

    if settings:
        steps.append(CujStep(order=order, action="Configure settings", route=settings.path, method=settings.method))

    return DiscoveredCUJ(
        id="onboarding-flow",
        name="User Onboarding",
        description="New user registration through initial configuration.",
        pattern="onboarding_flow",
        steps=steps,
        confidence=0.75,
    )


def _detect_search_flow(index: _RouteIndex) -> Optional[DiscoveredCUJ]:
    """Detect search/browse: search → filter → view detail."""
    search = _find_route(index, ["search", "query", "find"], "GET")
    listing = _find_route(index, ["list", "browse", "results"], "GET")
    detail = None

    # Look for detail endpoints (paths with {id} parameter)
    for route in index.all_routes:
        if route.method == "GET" and "{" in route.path and route != search and route != listing:
            detail = route
            break

    if not search and not listing:
        return None

    steps: list[CujStep] = []
    order = 1

    if search:
        steps.append(CujStep(order=order, action="Search for items", route=search.path, method=search.method))
        order += 1
    elif listing:
        steps.append(CujStep(order=order, action="Browse listings", route=listing.path, method=listing.method))
        order += 1

    if detail:
        steps.append(CujStep(order=order, action="View detail", route=detail.path, method=detail.method))

    if len(steps) < 2:
        return None

    return DiscoveredCUJ(
        id="search-flow",
        name="Search and Browse",
        description="Search or browse items and view details.",
        pattern="search_browse",
        steps=steps,
        confidence=0.7,
    )


def discover_cujs(features: List[FeatureArea]) -> List[DiscoveredCUJ]:
    """Auto-discover critical user journeys from feature areas and routes.

    Returns discovered CUJs sorted by confidence (highest first).
    """
    index = _RouteIndex.build(features)
    cujs: list[DiscoveredCUJ] = []

    # 1. Auth flow
    auth = _detect_auth_flow(index)
    if auth:
        cujs.append(auth)

    # 2. CRUD lifecycles
    cujs.extend(_detect_crud_lifecycle(features))

    # 3. Checkout flow
    checkout = _detect_checkout_flow(index)
    if checkout:
        cujs.append(checkout)

    # 4. Onboarding flow
    onboarding = _detect_onboarding_flow(index)
    if onboarding:
        cujs.append(onboarding)

    # 5. Search/browse flow
    search = _detect_search_flow(index)
    if search:
        cujs.append(search)

    # Sort by confidence descending
    cujs.sort(key=lambda c: c.confidence, reverse=True)

    return cujs


def to_cuj_config(
    discovered: List[DiscoveredCUJ],
    product_name: str = "",
) -> CUJConfig:
    """Convert discovered CUJs to a CUJConfig for the existing coverage system."""
    journeys: list[CUJ] = []

    for dcuj in discovered:
        apis = []
        components = []

        for step in dcuj.steps:
            if step.route:
                apis.append({
                    "method": step.method or "GET",
                    "endpoint": step.route,
                })

        for fid in dcuj.feature_ids:
            components.append(fid)

        journeys.append(CUJ(
            id=dcuj.id,
            name=dcuj.name,
            components=components,
            apis=apis,
            acceptance=[f"Step {s.order}: {s.action}" for s in dcuj.steps],
        ))

    return CUJConfig(
        product=product_name,
        journeys=journeys,
    )
