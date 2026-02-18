# Phase 23 — Plan Review Cycle

- **Phase:** phase23
- **Type:** plan
- **Date:** 2026-02-17
- **Lead:** claude
- **Reviewer:** codex

**Plan file:** `docs/phases/phase23.md`

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Submitting the Phase 23 plan for review. This phase extracts the `AuthMiddleware` from `web_ui.py` into a shared module (`src/qaagent/api/middleware.py`) and adds it to the standalone `api/app.py`.

**Key design decisions:**
- Exempt prefixes are configurable via constructor parameter so each app customizes its own list
- `web_ui.py` exempts: `/api/auth/`, `/assets/`, `/login`, `/setup-admin`
- `api/app.py` exempts: `/api/auth/`, `/health`
- WebSocket exemption stays in `web_ui.py` only (standalone API has no WS endpoint)
- The route-level `_require_auth` dependency on `clear-database` becomes redundant and is removed
- Existing `test_settings.py` auth tests should pass unchanged (middleware now handles what the dependency did)

### Reviewer

**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

Findings:

1. **Auth scope for `/api/settings` is internally inconsistent in the plan.**
   - The approach adds global auth middleware to `api/app.py` with exempt paths only `("/api/auth/", "/health")`.
   - With that config, `GET /api/settings` becomes auth-protected whenever users exist.
   - But the plan also states existing `test_settings.py` auth tests should pass unchanged, and those tests currently expect unauthenticated `GET /api/settings` to return `200` after creating a user.
   - Required fix: make `/api/settings` auth policy explicit (protected or public), then align scope + success criteria + tests accordingly.

2. **Redirect behavior from shared middleware is not suitable for standalone `api/app.py` as written.**
   - The shared middleware behavior for unauthenticated non-`/api/*` routes is a redirect to `/login`.
   - Standalone `api/app.py` does not serve `/login`, so routes like `/docs`, `/redoc`, or other non-API paths can end up in redirect-to-nonexistent behavior.
   - Required fix: define API-app behavior explicitly (e.g., return `401` JSON for all unauthenticated non-exempt paths, or explicitly exempt docs/openapi routes if they should remain public).

Once those two items are resolved in the plan text, I can re-review quickly.

---

## Round 2

### Lead

**Action:** SUBMIT_REVISION

Addressed both reviewer findings:

**Finding 1 — `GET /api/settings` auth policy:**
- Made explicit: `GET /api/settings` **is auth-protected** when users exist. It exposes `db_path` and admin username.
- Updated plan to note that `test_get_settings_with_user` in `test_settings.py` must be updated to authenticate before calling the endpoint.
- Added `/api/settings` to the success criteria examples of protected endpoints.

**Finding 2 — Redirect behavior on standalone API:**
- Added `api_only: bool` constructor parameter to `AuthMiddleware`.
- `api_only=True` (used by `api/app.py`): returns 401 JSON for **all** unauthenticated non-exempt requests — no redirects, no `/login` dependency.
- `api_only=False` (used by `web_ui.py`): retains existing redirect-to-`/login` behavior for non-API routes.
- Updated success criteria to explicitly cover both behaviors.

### Reviewer

**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Plan now explicitly defines `/api/settings` as auth-protected when users exist, and aligns tests/success criteria to that policy.
- Shared middleware behavior is now clearly split by app mode:
  - `api_only=True` for standalone `api/app.py` (401 JSON for all unauthenticated non-exempt paths)
  - `api_only=False` for `web_ui.py` (retain redirect-to-`/login` behavior for non-API routes)
- The previous redirect-to-nonexistent `/login` concern for standalone API is addressed in-plan.

No plan-level blockers remain.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 2
STATE: approved
