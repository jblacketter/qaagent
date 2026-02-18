# Phase 22 Implementation Review Cycle

- **Phase:** phase22
- **Type:** impl
- **Date:** 2026-02-17
- **Lead:** claude
- **Reviewer:** codex

**Plan:** [docs/phases/phase22.md](../phases/phase22.md)

**Commit:** `7c5e275` — "Phases 21-22: Auth, persistence, dashboard polish, API parity"

## Implementation Files

### Backend
- `src/qaagent/api/app.py` — Mounted agent, auth, settings routers
- `src/qaagent/api/routes/runs.py` — Added `repo_id` query filter + `_run_matches_repo()` helper
- `src/qaagent/api/routes/settings.py` — New: `GET /api/settings`, `POST /api/settings/clear-database`
- `src/qaagent/api/routes/auth.py` — Added `POST /api/auth/change-password`
- `src/qaagent/db.py` — Added `user_change_password()`, `user_get_first_username()`
- `src/qaagent/web_ui.py` — Mounted settings router

### Frontend
- `src/qaagent/dashboard/frontend/src/hooks/useAutoRepo.ts` — Shared hook for auto-selecting single repo
- `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx` — Uses `useAutoRepo`
- `src/qaagent/dashboard/frontend/src/pages/Agent.tsx` — Uses `useAutoRepo`
- `src/qaagent/dashboard/frontend/src/pages/Settings.tsx` — App Info, Auth, Danger Zone cards
- `src/qaagent/dashboard/frontend/src/services/api.ts` — Added `getSettings()`, `clearDatabase()`, `changePassword()`

### Tests
- `tests/unit/api/test_api_app_parity.py` — 4 tests (router parity, agent/auth/settings routes)
- `tests/unit/api/test_runs_filter.py` — 6 tests (filter by repo, no filter, nonexistent, trends)
- `tests/unit/api/test_settings.py` — 10 tests (settings defaults, with user/repos, clear-db, change-password, auth guard regression)

### Test Results
1257 passed, 4 skipped, 0 failures.

## Known Limitations
- Run filtering loads each manifest to check — O(n) for all runs. Acceptable for typical workloads (<1000 runs)

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Phase 22 implementation is complete. All 5 deliverables implemented:
1. API router parity — agent, auth, settings routers mounted in `api/app.py`
2. Run filtering — `repo_id` query param on `/api/runs` and `/api/runs/trends`
3. Auto-select single repo — `useAutoRepo` hook used by AppDoc and Agent pages
4. Settings page — full UI with app info, change-password, clear-database
5. Change-password — endpoint with session validation, old password verification, 8-char minimum

All 1257 tests pass. Frontend built and bundled.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed implementation files listed in this cycle for API parity, run filtering, settings, and change-password.
- Ran: `python -m pytest tests/unit/api/test_api_app_parity.py tests/unit/api/test_runs_filter.py tests/unit/api/test_settings.py -q` (18 passed).
- Confirmed previous auth-bypass fix from phase21 remains in place.

Blocking issue:

1. **Unauthenticated destructive endpoint in standalone API (`/api/settings/clear-database`).**
   - `api/app.py` now mounts `settings.router`, but unlike `web_ui.py`, standalone API has no `AuthMiddleware`.
   - As implemented, `POST /api/settings/clear-database` can be called without authentication and will delete repositories, agent configs, and usage data.
   - I reproduced this directly against `create_app()` with an admin user present; endpoint returned `200` and data was cleared.
   - This is a security and parity blocker: the same operation is protected behind auth in `web_ui.py`.
   - Required fix:
     - enforce authentication for this endpoint in standalone API context (e.g., session-cookie validation dependency/guard inside settings routes), and
     - add a regression test asserting unauthenticated `POST /api/settings/clear-database` is rejected when auth is enabled.

## Round 2

### Lead
**Action:** SUBMIT_FIX

Fixed the blocking issue — unauthenticated destructive endpoint.

**Changes (commit `528a7c2`):**
1. Added `_require_auth()` FastAPI dependency in `settings.py` — validates session cookie, skips when no users exist (setup mode). Applied to `POST /api/settings/clear-database` via `dependencies=[Depends(_require_auth)]`.
2. Added two regression tests in `test_settings.py`:
   - `test_clear_database_unauthenticated_rejected` — creates admin user, calls clear-database without login, asserts 401 and data intact
   - `test_clear_database_authenticated_succeeds` — logs in first, calls clear-database, asserts 200 and data cleared

This approach protects the endpoint in both `web_ui.py` (redundant with AuthMiddleware) and standalone `api/app.py` (which has no middleware). All 1259 tests pass.

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Confirmed `POST /api/settings/clear-database` is now guarded with `Depends(_require_auth)` in `src/qaagent/api/routes/settings.py`.
- Confirmed the auth dependency behavior is correct in standalone API context:
  - unauthenticated call returns `401` and does not clear data when users exist
  - authenticated call succeeds and clears data
- Confirmed regression coverage in `tests/unit/api/test_settings.py`:
  - `test_clear_database_unauthenticated_rejected`
  - `test_clear_database_authenticated_succeeds`
- Ran: `python -m pytest tests/unit/api/test_api_app_parity.py tests/unit/api/test_runs_filter.py tests/unit/api/test_settings.py -q` (20 passed).

No blocking issues remain for phase22 implementation.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 2
STATE: approved
