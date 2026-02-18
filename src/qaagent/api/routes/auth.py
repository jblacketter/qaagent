"""API routes for authentication (session-based)."""

from __future__ import annotations

import time
import threading
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from qaagent import db

router = APIRouter(tags=["auth"])

# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------

_rate_lock = threading.Lock()
_login_attempts: Dict[str, List[float]] = {}

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 minutes


def _check_rate_limit(ip: str) -> None:
    """Raise 429 if IP has exceeded login attempt limit."""
    now = time.time()
    with _rate_lock:
        attempts = _login_attempts.get(ip, [])
        # Prune old entries
        attempts = [t for t in attempts if now - t < WINDOW_SECONDS]
        _login_attempts[ip] = attempts
        if len(attempts) >= MAX_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail=f"Too many login attempts. Try again in {WINDOW_SECONDS // 60} minutes.",
            )


def _record_attempt(ip: str) -> None:
    with _rate_lock:
        _login_attempts.setdefault(ip, []).append(time.time())


def reset_rate_limits() -> None:
    """Clear all rate limit state (for testing)."""
    with _rate_lock:
        _login_attempts.clear()


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class AuthStatusResponse(BaseModel):
    setup_required: bool
    authenticated: bool
    username: Optional[str] = None


class SetupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Cookie config
# ---------------------------------------------------------------------------

COOKIE_NAME = "qaagent_session"
COOKIE_MAX_AGE = 86400  # 24 hours


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/auth/status")
def auth_status(request: Request) -> AuthStatusResponse:
    """Check authentication state."""
    if db.user_count() == 0:
        return AuthStatusResponse(setup_required=True, authenticated=False)

    token = request.cookies.get(COOKIE_NAME)
    if token:
        info = db.session_validate(token)
        if info:
            return AuthStatusResponse(
                setup_required=False,
                authenticated=True,
                username=info["username"],
            )

    return AuthStatusResponse(setup_required=False, authenticated=False)


@router.post("/auth/setup")
def setup_admin(body: SetupRequest, response: Response) -> AuthStatusResponse:
    """Create the initial admin account (only when no users exist)."""
    if db.user_count() > 0:
        raise HTTPException(status_code=403, detail="Admin account already exists.")

    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    user_id = db.user_create(body.username, body.password)
    token = db.session_create(user_id)
    _set_session_cookie(response, token)

    return AuthStatusResponse(
        setup_required=False,
        authenticated=True,
        username=body.username,
    )


@router.post("/auth/login")
def login(body: LoginRequest, request: Request, response: Response) -> AuthStatusResponse:
    """Authenticate with username/password."""
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)

    user_id = db.user_verify(body.username, body.password)
    if user_id is None:
        _record_attempt(ip)
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = db.session_create(user_id)
    _set_session_cookie(response, token)

    return AuthStatusResponse(
        setup_required=False,
        authenticated=True,
        username=body.username,
    )


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/auth/change-password")
def change_password(body: ChangePasswordRequest, request: Request) -> dict[str, str]:
    """Change the current user's password."""
    # Identify current user from session
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    info = db.session_validate(token)
    if not info:
        raise HTTPException(status_code=401, detail="Authentication required.")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")

    success = db.user_change_password(info["username"], body.old_password, body.new_password)
    if not success:
        raise HTTPException(status_code=401, detail="Old password is incorrect.")

    return {"status": "password_changed"}


@router.post("/auth/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    """Log out: clear session cookie and server-side session."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        db.session_delete(token)
    _clear_session_cookie(response)
    return {"status": "logged_out"}
