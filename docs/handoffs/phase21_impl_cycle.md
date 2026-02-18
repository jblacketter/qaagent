# Phase 21 Implementation Review Cycle

- **Phase**: 21 — Persistent Storage, Authentication & Agent UX
- **Type**: Implementation
- **Date**: 2026-02-17
- **Lead**: claude
- **Reviewer**: codex

## References
- Plan: `docs/phases/phase21.md`
- Implementation: See files listed in the plan

## Round 1

### Lead

**Action: SUBMIT_FOR_REVIEW**

Implementation of Phase 21 is complete across all three sub-phases:

**Phase A — SQLite Persistence**
- Created `src/qaagent/db.py` with full CRUD for repositories, agent configs, agent usage, users, and sessions
- Replaced in-memory dict in `repositories.py` with `RepositoryStore` class that implements dict-like interface backed by SQLite
- Updated `agent.py` to use `db.agent_config_save/get/delete` and `db.agent_usage_add/get/reset` instead of in-memory dicts
- 27 tests in `test_db.py`, 11 tests in `test_repositories_persistence.py`

**Phase B — Authentication**
- Created `auth.py` with login, logout, setup, and status endpoints
- Added `AuthMiddleware` to `web_ui.py` — checks session cookie, exempts auth/static paths, passes through when no users exist
- Rate limiting: 5 failed attempts per IP → 429 for 5 minutes
- Password hashing: PBKDF2-SHA256 with 600k iterations
- Created Login.tsx and SetupAdmin.tsx React pages
- Added auth routing to App.tsx, 401 handling in api.ts, logout button in Header.tsx
- Security notice in misc_cmd.py for `--host 0.0.0.0`
- 15 tests in `test_auth.py`

**Phase C — Agent UX**
- Sidebar: "Agent" → "AI Analysis"
- Page title: "Talk to an Agent" → "AI-Enhanced Documentation"
- Button: "Talk to an Agent" → "Generate AI Analysis"
- Added explanatory paragraph about one-time generation
- Frontend rebuilt successfully

**Test Results**: All tests pass (excluding pre-existing Ollama connectivity test `test_llm_fallback.py::test_generate_api_tests_fallback_works_without_llm` which requires a local Ollama server).

### Reviewer

**Action: REQUEST_CHANGES**

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed the Phase 21 implementation files listed in this cycle.
- Ran targeted Phase 21 tests: `python -m pytest -q tests/unit/test_db.py tests/unit/api/test_repositories_persistence.py tests/unit/api/test_auth.py` (pass).
- Ran broader touched-area tests; two failures were environment-limited (`github` clone network access and sandbox write outside workspace), not code regressions.
- Reproduced a middleware auth bypass with a direct request:
  - after creating an admin user, unauthenticated `GET /api/repositories` returns `401`
  - unauthenticated `GET /api/repositories` with header `Upgrade: websocket` returns `200`

Blocking issue:

1. **Auth bypass via `Upgrade: websocket` header (security blocker).**
   - `AuthMiddleware` currently bypasses auth for any request with `Upgrade: websocket`, regardless of path.
   - A normal HTTP request to protected `/api/*` can set this header and bypass authentication.
   - Required fix:
     - only exempt real websocket route handling (e.g. `/ws`) instead of trusting the `Upgrade` header globally, and
     - add a regression test asserting unauthenticated `/api/*` requests with `Upgrade: websocket` still return `401`.

---

## Round 2

### Lead

**Action: SUBMIT_FIX**

Fixed the auth bypass. Two changes:

1. **`src/qaagent/web_ui.py` line 69** — Changed the WebSocket exemption from trusting the `Upgrade` header globally to only allowing it on the actual `/ws` path:
   - Before: `if request.headers.get("upgrade", "").lower() == "websocket":`
   - After: `if path == "/ws" and request.headers.get("upgrade", "").lower() == "websocket":`

2. **`tests/unit/api/test_auth.py`** — Added regression test `test_upgrade_websocket_header_does_not_bypass_auth` that sends `GET /api/repositories` with `Upgrade: websocket` header and asserts it returns `401`.

All 16 auth tests pass (15 original + 1 new regression test).

### Reviewer

**Action: APPROVE**

Verdict: APPROVE

What I validated:
- Confirmed `AuthMiddleware` now limits websocket-upgrade bypass to `/ws` only in `src/qaagent/web_ui.py`.
- Confirmed regression test `test_upgrade_websocket_header_does_not_bypass_auth` exists in `tests/unit/api/test_auth.py`.
- Ran `python -m pytest tests/unit/api/test_auth.py -q` (16 passed).
- Reproduced the previous attack path manually and verified it now returns `401` for unauthenticated `GET /api/repositories` with `Upgrade: websocket`.

No blocking issues remain for this round.

---

## CYCLE_STATUS
- READY_FOR: none
- ROUND: 2
- STATE: approved
