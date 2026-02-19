# Phase 25 — Implementation Review Cycle

- **Phase:** phase25
- **Type:** impl
- **Date:** 2026-02-19
- **Lead:** claude
- **Reviewer:** codex

**Plan file:** `docs/phases/phase25.md`
**Scope:** Sub-phase 25a (Foundation — Models, Store, Tracker, CLI)

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Submitting the Phase 25a implementation for review. This implements the foundation layer of Branch Board: Pydantic models, SQLite store, git branch tracker, CLI commands, and API routes.

**Files created:**

| File | Purpose |
|------|---------|
| `src/qaagent/branch/__init__.py` | Package init |
| `src/qaagent/branch/models.py` | Pydantic models: `BranchStage` enum, `BranchCard`, `BranchCardUpdate`, `StoryLink`, `ChecklistItem`, `TestChecklist`, `BranchTestRun` |
| `src/qaagent/branch/store.py` | SQLite persistence: branch CRUD, checklist CRUD, test run CRUD |
| `src/qaagent/branch/tracker.py` | `BranchTracker` class — scans git repos, syncs branch lifecycle state, auto-detects story IDs from branch names |
| `src/qaagent/commands/branch_cmd.py` | CLI: `qaagent branch track`, `branch list`, `branch show`, `branch update` |
| `src/qaagent/api/routes/branches.py` | API: GET/PATCH/DELETE branches, POST scan, GET checklist, PATCH checklist items, GET test runs, GET stages |

**Files modified:**

| File | Change |
|------|--------|
| `src/qaagent/db.py` | Added 4 new tables: `branches`, `branch_checklists`, `branch_checklist_items`, `branch_test_runs` |
| `src/qaagent/commands/__init__.py` | Registered `branch_app` subcommand |
| `src/qaagent/api/app.py` | Included `branches.router` |
| `src/qaagent/web_ui.py` | Included `branches.router` |
| `tests/fixtures/cli_snapshots/pre_split_commands.json` | Updated snapshot to include `branch` command and subcommands |

**Key design decisions:**
- `repo_id` is `TEXT NOT NULL` in the `branches` table, matching `repositories.id TEXT PRIMARY KEY` (codex review finding from plan cycle)
- Lifecycle transitions: `created → active → merged` are automatic via git polling; `qa → released` are manual only (codex review finding from plan cycle)
- Story ID extraction uses regex patterns matching common branch naming conventions (`feature/PROJ-123-desc`, `bugfix/ABC-42`, etc.)
- `BranchTracker.scan()` does `git fetch --prune` first, then compares remote branches against the base branch
- Branch stats include commit count, files changed, and a summary built from commit messages
- Upsert logic preserves user-editable fields (story_id, story_url, notes) when auto-syncing

**Verification:**
- All module imports succeed
- Story ID extraction tested: `feature/PROJ-123-add-login` → `PROJ-123`, `bugfix/ABC-42` → `ABC-42`, `main` → `None`
- DB migration creates all 4 tables with correct column types
- CLI `branch track .` successfully scans current repo and creates cards
- CLI `branch list` displays tracked branches in a table
- All 9 API routes registered correctly
- Full test suite passes (excluding 2 pre-existing failures: `test_create_github` and an Ollama connectivity test)

### Reviewer

**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed implementation in:
  - `src/qaagent/branch/models.py`
  - `src/qaagent/branch/store.py`
  - `src/qaagent/branch/tracker.py`
  - `src/qaagent/commands/branch_cmd.py`
  - `src/qaagent/api/routes/branches.py`
  - `src/qaagent/db.py`
  - `src/qaagent/commands/__init__.py`
  - `src/qaagent/api/app.py`
  - `src/qaagent/web_ui.py`
- Ran targeted regression/parity tests:
  - `python -m pytest -q tests/unit/api/test_api_app_parity.py tests/unit/api/test_settings.py tests/integration/test_cli_split_parity.py` (all passed)
- Reproduced API behavior with branch data present:
  - `DELETE /api/repositories/repo1` -> `500`
  - `POST /api/settings/clear-database` -> `500`

Blocking issue:
1. **New `branches.repo_id -> repositories.id` FK causes repository deletion/reset flows to fail.**
   - `src/qaagent/db.py` adds `branches.repo_id TEXT NOT NULL REFERENCES repositories(id)` with no cascade.
   - Existing deletion/reset paths do not remove branch rows first:
     - `db.repo_delete()` (used by `/api/repositories/{repo_id}`) now raises `sqlite3.IntegrityError`.
     - `clear_database()` in `src/qaagent/api/routes/settings.py` executes `DELETE FROM repositories;` and now fails when branch rows exist.
   - User-visible regression: both endpoints return 500 once any branch card exists.
   - Required fix:
     - either add `ON DELETE CASCADE` to the branch FK and ensure migration compatibility, or
     - explicitly delete branch-related rows before deleting repositories,
     - and add regression tests covering both endpoints with branch data present.

## Round 2

### Lead

**Action:** SUBMIT_REVISION

Addressed the FK cascade issue:

**Fix 1 — `ON DELETE CASCADE` on all branch FK constraints in `db.py`:**
- `branches.repo_id` → `REFERENCES repositories(id) ON DELETE CASCADE`
- `branch_checklists.branch_id` → `REFERENCES branches(id) ON DELETE CASCADE`
- `branch_checklist_items.checklist_id` → `REFERENCES branch_checklists(id) ON DELETE CASCADE`
- `branch_test_runs.branch_id` → `REFERENCES branches(id) ON DELETE CASCADE`

This matches the existing pattern used by `sessions` → `users(id) ON DELETE CASCADE`.

**Fix 2 — Explicit delete order in `clear_database()` (`settings.py`):**
- Added `DELETE FROM branch_checklist_items`, `branch_checklists`, `branch_test_runs`, `branches` before `DELETE FROM repositories` as a belt-and-suspenders measure. Even though CASCADE handles it, `executescript` runs without FK enforcement (no `PRAGMA foreign_keys=ON` per statement), so explicit ordering ensures correctness regardless.

**Fix 3 — Simplified `branch_delete()` in `store.py`:**
- Removed manual cascade deletes (checklist items, checklists, test runs) since the FK cascade now handles it. Single `DELETE FROM branches WHERE id = ?`.

**Verification:**
- Tested repo deletion with branch data present: branch rows cascade-deleted correctly (0 remaining)
- Tested `clear_database` flow: all branch + repo rows cleared correctly
- Full test suite passes (excluding 2 pre-existing unrelated failures)

### Reviewer

**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Confirmed Round 2 code changes are present in:
  - `src/qaagent/db.py` (branch FK cascades added)
  - `src/qaagent/api/routes/settings.py` (explicit branch-table delete ordering)
  - `src/qaagent/branch/store.py` (`branch_delete` simplified to rely on FK cascade)
- Ran targeted tests:
  - `python -m pytest -q tests/unit/test_db.py tests/unit/api/test_repositories_persistence.py tests/unit/api/test_settings.py` (all passed)
- Reproduced behavior checks:
  - Fresh DB created with current schema: both endpoints pass (`DELETE /api/repositories/{id}` = 200, `POST /api/settings/clear-database` = 200)
  - Legacy DB with Round 1 schema (no cascade FKs): `db.repo_delete()` still fails with `sqlite3.IntegrityError: FOREIGN KEY constraint failed`

Blocking issue:
1. **Migration compatibility gap: existing Round 1 DBs still fail repository deletion.**
   - `src/qaagent/db.py` uses `CREATE TABLE IF NOT EXISTS`, which does not alter existing FK constraints.
   - Adding `ON DELETE CASCADE` in table definitions fixes only newly created databases.
   - For users who already have branch tables from Round 1, `db.repo_delete()` (and thus `DELETE /api/repositories/{repo_id}`) can still raise FK errors.
   - Required fix:
     - add a compatibility migration path for existing DBs (recreate branch tables with cascade or explicitly delete branch rows in `repo_delete()` before deleting repository),
     - and add regression tests that cover delete behavior against pre-cascade schema state (or an equivalent compatibility test).

## Round 3

### Lead

**Action:** SUBMIT_REVISION

Addressed the migration compatibility gap:

**Fix — Explicit branch cleanup in `repo_delete()` (`db.py`):**
- Added explicit DELETE statements for `branch_checklist_items`, `branch_checklists`, `branch_test_runs`, and `branches` before deleting the repository row.
- This runs before the repo DELETE, so it works regardless of whether the FK has `ON DELETE CASCADE` (new DBs) or not (legacy Round 1 DBs).
- The `ON DELETE CASCADE` on the FK constraint is kept as defense-in-depth for new DBs.
- Same approach already used in `clear_database()` in settings.py (added in Round 2).

**Regression tests added:**
1. `test_db.py::TestRepoCRUD::test_delete_cascades_branch_data` — Creates a repo with a branch card, checklist, checklist item, and test run, then deletes the repo and verifies all 4 child tables are empty.
2. `test_settings.py::test_clear_database_with_branch_data` — Creates a repo with a branch card, calls `POST /api/settings/clear-database`, and verifies both repos and branches are cleared.

**Verification:**
- All 38 DB + settings tests pass (including 2 new regression tests)
- Full test suite passes (excluding 2 pre-existing unrelated failures)

### Reviewer

**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Confirmed Round 3 compatibility fix in `src/qaagent/db.py`:
  - `repo_delete()` now explicitly deletes branch child rows (`branch_checklist_items`, `branch_checklists`, `branch_test_runs`, `branches`) before deleting the repository row.
  - This makes deletion robust for both pre-cascade and cascade schemas.
- Confirmed regression tests are present:
  - `tests/unit/test_db.py::TestRepoCRUD::test_delete_cascades_branch_data`
  - `tests/unit/api/test_settings.py::test_clear_database_with_branch_data`
- Ran targeted tests:
  - `python -m pytest -q tests/unit/test_db.py::TestRepoCRUD::test_delete_cascades_branch_data tests/unit/api/test_settings.py::test_clear_database_with_branch_data tests/unit/api/test_repositories_persistence.py::TestPersistenceAcrossRestart::test_delete_persists` (passed)
- Ran compatibility simulation against a legacy Round 1-style schema (no cascade FKs on branch tables):
  - `db.repo_delete('repo1')` succeeded
  - Verified all related rows were removed from `repositories`, `branches`, `branch_checklists`, `branch_checklist_items`, and `branch_test_runs`

No blocking issues remain for Phase 25a implementation.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 3
STATE: approved
