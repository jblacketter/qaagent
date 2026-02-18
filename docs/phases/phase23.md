# Phase 23: Standalone API Auth Middleware

## Summary
Extract `AuthMiddleware` from `web_ui.py` into a shared module and add it to the standalone `api/app.py` so all sensitive endpoints are protected by session-based authentication — not just `clear-database`.

## Scope
1. **Extract AuthMiddleware** — Move the `AuthMiddleware` class from `web_ui.py` into `src/qaagent/api/middleware.py` with configurable exempt prefixes
2. **Protect standalone API** — Add the middleware to `api/app.py` with API-appropriate exempt paths (`/api/auth/`, `/health`)
3. **Remove route-level auth guard** — Delete the `_require_auth` dependency from `settings.py` (now redundant)
4. **Test coverage** — New test suite for middleware behavior on the standalone API app

## Technical Approach
- `AuthMiddleware` constructor takes two config params:
  - `exempt_prefixes: tuple[str, ...]` — paths that skip auth entirely
  - `api_only: bool = False` — when `True`, all unauthenticated requests get 401 JSON (no redirects). When `False`, non-`/api/` paths redirect to `/login`.
- `web_ui.py` passes: `exempt_prefixes=("/api/auth/", "/assets/", "/login", "/setup-admin"), api_only=False`
- `api/app.py` passes: `exempt_prefixes=("/api/auth/", "/health"), api_only=True`
- With `api_only=True`, the standalone API returns 401 JSON for all unauthenticated requests (including `/docs`, `/redoc`, or any non-`/api/` path). No redirect-to-nonexistent-login behavior.
- WebSocket exemption stays in `web_ui.py` only (standalone API has no WebSocket endpoint)
- **`GET /api/settings` is auth-protected** when users exist. It exposes `db_path` and admin username — should not be public. Existing `test_get_settings_with_user` test must be updated to authenticate first.

## Files Modified/Created
| File | Action |
|------|--------|
| `src/qaagent/api/middleware.py` | **Create** — shared AuthMiddleware with configurable exempt prefixes |
| `src/qaagent/web_ui.py` | Modify — remove inline AuthMiddleware, import from shared module |
| `src/qaagent/api/app.py` | Modify — add AuthMiddleware with API-specific exempt paths |
| `src/qaagent/api/routes/settings.py` | Modify — remove `_require_auth` dependency and function |
| `tests/unit/api/test_api_auth_middleware.py` | **Create** — middleware tests for standalone API |
| `tests/unit/api/test_settings.py` | Modify — `test_get_settings_with_user` must login before calling `GET /api/settings` |

## Success Criteria
- Unauthenticated requests to protected standalone API endpoints return 401 (e.g., `DELETE /api/repositories/x`, `GET /api/settings`, `POST /api/settings/clear-database`)
- `/api/auth/status` and `/health` remain accessible without auth
- Setup mode (no users) allows all requests through
- Authenticated requests with valid session cookie succeed
- Standalone API returns 401 JSON for **all** unauthenticated non-exempt paths (no redirects, even for `/docs` or non-`/api/` routes)
- `web_ui.py` retains redirect-to-`/login` behavior for unauthenticated non-API routes
- Existing `test_settings.py` tests pass after updating `test_get_settings_with_user` to authenticate
- Full test suite passes
