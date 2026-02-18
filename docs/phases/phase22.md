# Phase 22: Dashboard Polish & API Parity

## Summary
Close usability gaps in the dashboard and make the standalone REST API feature-complete with the web UI app.

## Scope
1. **API Router Parity** — Mount agent, auth, and settings routers in `api/app.py` so the standalone API matches `web_ui.py`
2. **Run Filtering** — Add `repo_id` query parameter to `GET /api/runs` and `GET /api/runs/trends` for server-side filtering
3. **Auto-Select Single Repo** — Create `useAutoRepo` hook so AppDoc and Agent pages auto-redirect when only one repo exists
4. **Settings Page** — Replace placeholder with app info, change-password form, and clear-database danger zone
5. **Change Password** — `POST /api/auth/change-password` endpoint with `db.user_change_password()` helper

## Technical Approach
- Run filtering matches `manifest.target.name` (lowercased, hyphenated) against `repo_id`, with fallback to path comparison
- `useAutoRepo` hook reads `?repo=` from URL search params, fetches repos list, auto-sets param when exactly one exists
- Settings endpoint reads package version via `importlib.metadata`, DB path from module state, counts from DB/RunManager
- Change-password validates session cookie, verifies old password, enforces 8-char minimum

## Files Modified/Created
| File | Action |
|------|--------|
| `src/qaagent/api/app.py` | Modified — mount agent + auth + settings routers |
| `src/qaagent/api/routes/runs.py` | Modified — add `repo_id` filter param |
| `src/qaagent/api/routes/settings.py` | Created — settings/info endpoint + clear-database |
| `src/qaagent/api/routes/auth.py` | Modified — add change-password endpoint |
| `src/qaagent/db.py` | Modified — add `user_change_password()`, `user_get_first_username()` |
| `src/qaagent/web_ui.py` | Modified — mount settings router |
| `frontend/src/hooks/useAutoRepo.ts` | Created — auto-select single repo hook |
| `frontend/src/pages/AppDoc.tsx` | Modified — use `useAutoRepo` |
| `frontend/src/pages/Agent.tsx` | Modified — use `useAutoRepo` |
| `frontend/src/pages/Settings.tsx` | Modified — full settings UI |
| `frontend/src/services/api.ts` | Modified — add settings/changePassword methods |
| `tests/unit/api/test_api_app_parity.py` | Created |
| `tests/unit/api/test_runs_filter.py` | Created |
| `tests/unit/api/test_settings.py` | Created |

## Success Criteria
- All router routes from `web_ui.py` also exist in `api/app.py`
- `GET /api/runs?repo_id=alpha` returns only matching runs; omitting param returns all
- AppDoc/Agent pages auto-redirect to `?repo=<id>` when one repo exists
- Settings page shows version, DB path, repo count, run count, admin username
- Change-password validates old password and enforces 8-char minimum
- `POST /api/settings/clear-database` removes repos, agent configs, usage data
- 1257 tests pass, 0 failures
