"""Heuristic user role discovery from route analysis."""

from __future__ import annotations

import re
from typing import List

from .models import FeatureArea, UserRole

# Route path patterns that indicate specific roles
_AUTH_PATTERNS = re.compile(
    r"(login|signin|sign-in|register|signup|sign-up|auth|session|password|reset-password|verify)",
    re.IGNORECASE,
)
_ADMIN_PATTERNS = re.compile(
    r"(admin|backoffice|back-office|management|moderator)",
    re.IGNORECASE,
)
_API_PATTERNS = re.compile(
    r"(api[_-]?key|token|oauth|client[_-]?credentials|webhook)",
    re.IGNORECASE,
)


def discover_roles(features: List[FeatureArea]) -> List[UserRole]:
    """Discover user roles from feature areas and their routes.

    Heuristics:
    - Auth-related routes → "User" role (authenticated end user)
    - Admin routes → "Admin" role
    - API key / token routes → "API Consumer" role
    - No auth routes at all → single "User (unauthenticated)" role
    """
    has_auth = False
    has_admin = False
    has_api_consumer = False
    auth_feature_ids: List[str] = []
    admin_feature_ids: List[str] = []
    api_feature_ids: List[str] = []
    all_feature_ids = [f.id for f in features]

    for feature in features:
        paths = [r.path for r in feature.routes]
        path_blob = " ".join(paths)

        if _AUTH_PATTERNS.search(path_blob):
            has_auth = True
            auth_feature_ids.append(feature.id)

        if _ADMIN_PATTERNS.search(path_blob):
            has_admin = True
            admin_feature_ids.append(feature.id)

        if _API_PATTERNS.search(path_blob):
            has_api_consumer = True
            api_feature_ids.append(feature.id)

        # Also check feature-level auth flag
        if feature.auth_required:
            has_auth = True
            if feature.id not in auth_feature_ids:
                auth_feature_ids.append(feature.id)

    roles: List[UserRole] = []

    if has_auth:
        # Authenticated user gets access to all non-admin features
        user_features = [
            fid for fid in all_feature_ids if fid not in admin_feature_ids
        ]
        roles.append(UserRole(
            id="user",
            name="User",
            description="Authenticated end user who can access core application features.",
            permissions=["login", "view", "create", "update"],
            associated_features=user_features,
        ))

    if has_admin:
        roles.append(UserRole(
            id="admin",
            name="Admin",
            description="Administrator with access to management and configuration features.",
            permissions=["login", "view", "create", "update", "delete", "manage"],
            associated_features=admin_feature_ids + [
                fid for fid in all_feature_ids if fid not in admin_feature_ids
            ],
        ))

    if has_api_consumer:
        roles.append(UserRole(
            id="api-consumer",
            name="API Consumer",
            description="External system or developer accessing the API via tokens or keys.",
            permissions=["api_access", "read", "write"],
            associated_features=api_feature_ids,
        ))

    if not roles:
        # No auth detected — single unauthenticated user role
        roles.append(UserRole(
            id="user-unauthenticated",
            name="User (unauthenticated)",
            description="Public user with access to all application features. No authentication required.",
            permissions=["view"],
            associated_features=all_feature_ids,
        ))

    return roles
