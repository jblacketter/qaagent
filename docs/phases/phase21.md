# Phase 21: Persistent Storage, Authentication & Agent UX

## Summary
Add SQLite persistence so repository registrations survive server restarts, session-based authentication to protect the web UI on LAN, and fix misleading Agent page labels.

## Scope
- **Phase A**: SQLite persistence layer (`db.py`), SQLite-backed `RepositoryStore`, agent config/usage persistence
- **Phase B**: Authentication — users/sessions tables, auth API routes, AuthMiddleware, login/setup React pages, logout button, 401 handling, rate limiting, security notice for `--host 0.0.0.0`
- **Phase C**: Agent UX relabeling — "Agent" → "AI Analysis", "Talk to an Agent" → "AI-Enhanced Documentation" / "Generate AI Analysis", explanatory paragraph

## Technical Approach
- Zero new Python dependencies — uses stdlib `sqlite3` for persistence and `hashlib.pbkdf2_hmac` for password hashing
- `RepositoryStore` class implements dict-like interface (`__contains__`, `__getitem__`, `__setitem__`, `__delitem__`, `get()`, `values()`, `clear()`) backed by SQLite, preserving the existing import interface
- API keys stored as base64 at rest (prevents casual plaintext exposure)
- Session-based auth with httponly + SameSite=Strict cookies
- Login rate limiting: 5 attempts per IP in 5-minute window (in-memory)
- AuthMiddleware exempts `/api/auth/*`, `/assets/`, `/login`, `/setup-admin`, WebSocket upgrades
- When no users exist (first run), middleware passes all requests through

## Files Created
| File | Purpose |
|------|---------|
| `src/qaagent/db.py` | SQLite persistence layer (repos, agent configs/usage, users, sessions) |
| `src/qaagent/api/routes/auth.py` | Auth API endpoints (status, setup, login, logout) |
| `frontend/src/pages/Login.tsx` | Login page |
| `frontend/src/pages/SetupAdmin.tsx` | First-run admin setup page |
| `tests/unit/test_db.py` | DB CRUD round-trip tests |
| `tests/unit/api/test_repositories_persistence.py` | Persistence-across-restart tests |
| `tests/unit/api/test_auth.py` | Auth flow tests (setup, login, logout, 401, rate limiting, session expiry) |

## Files Modified
| File | Change |
|------|--------|
| `src/qaagent/api/routes/repositories.py` | Replace in-memory dict with `RepositoryStore` class, add `_persist()` helper |
| `src/qaagent/api/routes/agent.py` | Replace `_configs`/`_usage` dicts with `db.*` calls |
| `src/qaagent/web_ui.py` | Add `AuthMiddleware`, mount auth router |
| `src/qaagent/commands/misc_cmd.py` | Security notice when `--host 0.0.0.0` |
| `frontend/src/App.tsx` | Auth status check, `/login` and `/setup-admin` routes |
| `frontend/src/services/api.ts` | 401 → redirect to `/login` |
| `frontend/src/components/Layout/Header.tsx` | Logout button |
| `frontend/src/components/Layout/Sidebar.tsx` | "Agent" → "AI Analysis" |
| `frontend/src/pages/Agent.tsx` | Label changes + explanatory text |
| `tests/api/test_agent.py` | Updated to use `db.*` instead of removed `_configs`/`_usage` |
| `tests/api/test_doc_repo_aware.py` | Added `_isolated_db` fixture |
| `tests/api/test_generate_tests.py` | Added `_isolated_db` fixture |
| `tests/integration/test_doc_pipeline.py` | Replaced `_clear_repos` with `_isolated_db` |
| `tests/unit/api/routes/test_repositories.py` | Added `_isolated_db` fixture |

## Success Criteria
1. Add repo → restart server → repo still listed
2. Configure agent key → restart → key still configured
3. Fresh DB → redirected to setup-admin → create admin → login → access app
4. Incognito/new client → redirected to login
5. 6 bad login attempts → rate limited (429)
6. Logout works, clears session
7. `--host 0.0.0.0` prints security warning
8. Sidebar says "AI Analysis", page title says "AI-Enhanced Documentation", button says "Generate AI Analysis"
9. All tests pass (excluding pre-existing Ollama connectivity test)
