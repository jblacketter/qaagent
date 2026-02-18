# Phase 23 — Implementation Review Cycle

- **Phase:** phase23
- **Type:** impl
- **Date:** 2026-02-17
- **Lead:** claude
- **Reviewer:** codex

**Plan file:** `docs/phases/phase23.md`

**Implementation files:**
- `src/qaagent/api/middleware.py` (new)
- `src/qaagent/api/app.py` (modified)
- `src/qaagent/web_ui.py` (modified)
- `src/qaagent/api/routes/settings.py` (modified)
- `tests/unit/api/conftest.py` (new)
- `tests/integration/conftest.py` (new)
- `tests/unit/api/test_api_auth_middleware.py` (new)
- `tests/unit/api/test_settings.py` (modified)

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Implementation complete. Summary of changes:

**`src/qaagent/api/middleware.py` (new):**
- Shared `AuthMiddleware` with configurable `exempt_prefixes` tuple and `api_only` bool
- `api_only=True`: returns 401 JSON for all unauthenticated non-exempt requests (no redirects)
- `api_only=False`: redirects non-`/api/` paths to `/login` (web UI behavior)
- Setup mode: when `db.user_count() == 0`, all requests pass through

**`src/qaagent/web_ui.py`:**
- Removed inline `AuthMiddleware` class and `_AUTH_EXEMPT_PREFIXES` constant
- Imports `AuthMiddleware` from `qaagent.api.middleware`
- Passes `exempt_prefixes=("/api/auth/", "/assets/", "/login", "/setup-admin", "/ws")`, `api_only=False`
- WebSocket `/ws` path added to exempt prefixes (simpler than the original upgrade-header check, and functionally equivalent since `/ws` is only a WebSocket endpoint)

**`src/qaagent/api/app.py`:**
- Imports and adds `AuthMiddleware` with `exempt_prefixes=("/api/auth/", "/health")`, `api_only=True`
- Also fixed a minor formatting issue (stray newline in `allow_methods`)

**`src/qaagent/api/routes/settings.py`:**
- Removed `_require_auth` function and `Depends` import
- Removed `dependencies=[Depends(_require_auth)]` from `clear-database` endpoint

**`tests/unit/api/conftest.py` (new):**
- Autouse fixture `_isolate_db` ensures every API test gets a fresh temporary database
- Prevents auth middleware from blocking tests when developer's real DB has users
- Removed duplicate `_isolate_db` fixtures from `test_settings.py` and `test_api_auth_middleware.py`

**`tests/integration/conftest.py` (new):**
- Same autouse `_isolate_db` fixture for integration tests

**`tests/unit/api/test_api_auth_middleware.py` (new — 12 tests):**
- Setup mode allows all endpoints
- Exempt paths (`/api/auth/`, `/health`) always accessible
- Unauthenticated requests return 401 for protected endpoints (`GET /api/settings`, `GET /api/repositories`, `DELETE /api/repositories/x`, `POST /api/settings/clear-database`)
- Non-API paths return 401 (not redirect) on standalone API
- Authenticated requests succeed

**`tests/unit/api/test_settings.py`:**
- `test_get_settings_with_user` now logs in before calling `GET /api/settings`

**Test results:** 1271 passed, 4 skipped, 0 failures.

### Reviewer

**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Reviewed implementation across:
  - `src/qaagent/api/middleware.py`
  - `src/qaagent/api/app.py`
  - `src/qaagent/web_ui.py`
  - `src/qaagent/api/routes/settings.py`
  - `tests/unit/api/conftest.py`
  - `tests/integration/conftest.py`
  - `tests/unit/api/test_api_auth_middleware.py`
  - `tests/unit/api/test_settings.py`
- Ran:
  - `python -m pytest tests/unit/api/test_api_auth_middleware.py tests/unit/api/test_settings.py tests/unit/api/test_api_app_parity.py tests/unit/api/test_runs_filter.py -q` (32 passed)
  - `python -m pytest tests/unit/api/test_auth.py -q` (16 passed)
- Confirmed:
  - standalone API enforces auth via shared middleware with `api_only=True`
  - `/api/auth/*` and `/health` remain unauthenticated
  - `GET /api/settings` and `POST /api/settings/clear-database` are protected when users exist
  - web UI retains redirect-style behavior for unauthenticated non-API routes

No blocking issues remain for phase23 implementation.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 1
STATE: approved
