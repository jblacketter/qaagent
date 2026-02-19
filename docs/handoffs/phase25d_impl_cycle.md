# Phase 25d — Implementation Review Cycle

- **Phase:** phase25d
- **Type:** impl
- **Date:** 2026-02-19
- **Lead:** claude
- **Reviewer:** codex

**Plan file:** `docs/phases/phase25.md` (sub-phase 25d)

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 25d implementation: Test Execution & Promotion.

**Files created:**

| File | Purpose |
|------|---------|
| `src/qaagent/branch/test_executor.py` | `generate_branch_tests()` — discovers routes from source, filters to changed files via diff, generates pytest tests. `run_branch_tests()` — runs generated tests via PytestRunner, returns results. Tests output to `~/.qaagent/branch-tests/<branch_id>/`. |

**Files modified:**

| File | Change |
|------|--------|
| `src/qaagent/branch/store.py` | Added `test_run_promote(run_db_id)` — sets `promoted_to_regression = 1` for a test run |
| `src/qaagent/api/routes/branches.py` | Added 3 endpoints: `POST /branches/{id}/generate-tests`, `POST /branches/{id}/run-tests`, `PATCH /branches/test-runs/{id}/promote` |
| `src/qaagent/commands/branch_cmd.py` | Added 2 CLI commands: `branch generate-tests <id>`, `branch run-tests <id>` |
| `tests/fixtures/cli_snapshots/pre_split_commands.json` | Added `generate-tests` and `run-tests` to branch subcommands |
| `src/qaagent/dashboard/frontend/src/types/index.ts` | Added `BranchGenerateResult` interface |
| `src/qaagent/dashboard/frontend/src/services/api.ts` | Added 3 API methods: `generateTests()`, `runTests()`, `promoteTestRun()` |
| `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx` | Added "Automated Tests" section with Generate Tests button, Run Tests button, generation result feedback, and per-run Promote action |

**Design decisions:**

- **Route-based test generation (not checklist-based)**: The existing generators take `List[Route]`, not checklist items. Rather than building an LLM-powered checklist-to-code converter (complex, unreliable), we reuse the proven route-based pipeline: diff → discover routes → filter to changed files → generate tests. The checklist remains a human QA tool; automated tests complement it.
- **File-metadata filtering**: Routes discovered from source code carry `metadata["file"]` from framework parsers. We filter by matching against the branch's changed file set. If no file metadata matches (e.g., OpenAPI-sourced routes), we fall back to generating tests for all routes when route files changed.
- **Separate generate + run steps**: Generation and execution are separate actions (not combined) because: (1) users may want to inspect generated tests before running, (2) running requires the target app to be accessible, (3) generation can be repeated without running.
- **Promote = DB flag only**: "Promote to regression" sets `promoted_to_regression = 1` in the DB. Actual file copying to a regression directory is deferred to a future phase. The flag serves as a marker for which runs were approved for regression.
- **Output directory**: `~/.qaagent/branch-tests/<branch_id>/` — isolated per branch, easy to inspect and clean up.
- **PytestRunner default**: We default to pytest as the runner. Future phases can add suite_type selection (behave, playwright).

**Verification:**
- `npm run build` succeeds (0 TypeScript errors)
- All 63 branch unit tests pass
- All 33 parity tests pass (CLI + API)
- CLI snapshot includes `generate-tests` and `run-tests` subcommands
- API endpoints register correctly (verified via parity tests)
- Dashboard "Automated Tests" section renders with Generate/Run/Promote buttons

### Reviewer

**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed:
  - `src/qaagent/branch/test_executor.py`
  - `src/qaagent/branch/store.py`
  - `src/qaagent/api/routes/branches.py`
  - `src/qaagent/commands/branch_cmd.py`
  - `src/qaagent/dashboard/frontend/src/components/Branch/BranchDetail.tsx`
  - `src/qaagent/dashboard/frontend/src/services/api.ts`
  - `src/qaagent/dashboard/frontend/src/types/index.ts`
  - `tests/fixtures/cli_snapshots/pre_split_commands.json`
- Ran:
  - `npm run build` (passes)
  - `python -m pytest -q tests/unit/branch tests/integration/test_cli_split_parity.py tests/unit/api/test_api_app_parity.py` (passes)
- Confirmed on Windows path semantics:
  - route metadata path strings use backslashes (e.g., `src\\api\\users.py`)
  - git diff paths use forward slashes (e.g., `src/api/users.py`)
  - current equality filter in `generate_branch_tests()` fails without normalization

Blocking issues:
1. **Windows path-separator mismatch breaks changed-route filtering in test generation.**
   - In `src/qaagent/branch/test_executor.py`, filtering uses exact string equality:
     - `r.metadata.get("file") in changed_paths`
   - `changed_paths` comes from git diff output (`/` separators), while route metadata file paths come from discovery parsers using `str(Path(...))` (platform separators, `\\` on Windows).
   - Impact: on Windows, changed-route scoping fails. For route diffs it falls back to generating tests for all routes; for non-route diffs it often reports no matching routes.
   - Required fix: normalize both sides to a common representation before comparison (for example, convert to POSIX-style strings).
2. **No automated tests cover phase25d backend behavior.**
   - I found no tests for:
     - `generate_branch_tests()` / `run_branch_tests()`
     - new API endpoints: `/branches/{id}/generate-tests`, `/branches/{id}/run-tests`, `/branches/test-runs/{id}/promote`
     - `store.test_run_promote()`
   - Required fix: add targeted unit/API tests, including a regression test for Windows-style path normalization in route filtering.

## Round 2

### Lead

**Action:** SUBMIT_FOR_REVIEW

Addressed both blocking issues from Round 1.

**Fix 1: Windows path-separator mismatch**

- Added `_posix(path)` helper to `test_executor.py` that normalizes `\` to `/`.
- Applied `_posix()` to both sides of the comparison: `changed_paths` (from git diff) and `route.metadata["file"]` (from framework parsers).
- Now `src\api\users.py` (Windows metadata) matches `src/api/users.py` (git diff) correctly.

**Fix 2: Added comprehensive unit tests (13 new tests)**

| File | Tests | Coverage |
|------|-------|----------|
| `tests/unit/branch/test_test_executor.py` | 11 tests | `_posix()` normalization (5 tests including Windows regression), `generate_branch_tests()` pipeline with mocked deps (6 tests: empty diff, no routes, filtering, Windows path match, OpenAPI fallback, non-route diff) |
| `tests/unit/branch/test_store_promote.py` | 2 tests | `test_run_promote()` — existing run returns True, nonexistent returns False |

**Key test design decisions:**
- Patched at original module locations (`qaagent.branch.diff_analyzer.DiffAnalyzer`, `qaagent.analyzers.route_discovery.discover_routes`, etc.) since `test_executor.py` uses lazy imports inside function bodies.
- Used `patch.object(branch_store, "db")` for store tests to avoid pytest collecting `test_run_promote` as a test (function name starts with `test_`).

**Verification:**
- All 76 branch unit tests pass
- All 33 parity tests pass
- `npm run build` succeeds

### Reviewer

**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Confirmed path normalization fix in `src/qaagent/branch/test_executor.py`:
  - `_posix()` introduced and applied to both changed paths and route metadata file paths.
- Confirmed new tests were added and passing:
  - `tests/unit/branch/test_test_executor.py`
  - `tests/unit/branch/test_store_promote.py`
- Ran:
  - `python -m pytest -q tests/unit/branch tests/integration/test_cli_split_parity.py tests/unit/api/test_api_app_parity.py` (passes)
  - `npm run build` (passes)

Blocking issue:
1. **Coverage remains incomplete for new phase25d runtime/API surface.**
   - New behavior added in this phase is still untested by automated tests:
     - `run_branch_tests()` path in `src/qaagent/branch/test_executor.py`
     - new API endpoints in `src/qaagent/api/routes/branches.py`:
       - `POST /branches/{id}/generate-tests`
       - `POST /branches/{id}/run-tests`
       - `PATCH /branches/test-runs/{id}/promote`
   - Current additions test generation filtering and store promote helper, but not endpoint behavior/error mapping and not test execution flow.
   - Required fix: add targeted unit/API tests for these code paths (success + key failure modes, including “no generated tests” for run endpoint and not-found cases for promote endpoint).

## Round 3

### Lead

**Action:** SUBMIT_FOR_REVIEW

Added comprehensive tests for `run_branch_tests()` and all 3 new API endpoints.

**New tests added:**

| File | Tests | Coverage |
|------|-------|----------|
| `tests/unit/branch/test_test_executor.py` | 3 new tests in `TestRunBranchTests` | `run_branch_tests()`: no test dir raises `FileNotFoundError`, empty dir raises, success returns correct counts and run_id |
| `tests/unit/api/routes/test_branches.py` | 7 new tests (new file) | `POST /generate-tests`: branch not found (404), repo not found (404). `POST /run-tests`: branch not found (404), no generated tests (400), success stores and returns run. `PATCH /test-runs/{id}/promote`: not found (404), success (200). |

**Test approach:**
- API endpoint tests use `FastAPI TestClient` (same pattern as existing `tests/unit/api/routes/test_runs.py`)
- `store` module patched at `qaagent.api.routes.branches.store` since it's a module-level import
- Lazy imports (`run_branch_tests`, `db.repo_get`) patched at their source module locations
- `run_branch_tests()` tests use `tmp_path` fixture with real filesystem (test dir exists/doesn't exist, has test files/doesn't)

**Verification:**
- All 86 branch + API tests pass
- All 33 parity tests pass
- `npm run build` succeeds

### Reviewer

**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Confirmed Windows path-normalization fix in `src/qaagent/branch/test_executor.py`:
  - `_posix()` normalization is applied to both changed diff paths and route metadata file paths before filtering.
- Confirmed added test coverage for previously missing phase25d surfaces:
  - `tests/unit/branch/test_test_executor.py` includes `run_branch_tests()` coverage (missing dir, empty dir, success path).
  - `tests/unit/api/routes/test_branches.py` covers new endpoints:
    - `POST /api/branches/{id}/generate-tests`
    - `POST /api/branches/{id}/run-tests`
    - `PATCH /api/branches/test-runs/{id}/promote`
  - `tests/unit/branch/test_store_promote.py` covers `store.test_run_promote()`.
- Ran validation:
  - `python -m pytest -q tests/unit/branch tests/unit/api/routes/test_branches.py tests/integration/test_cli_split_parity.py tests/unit/api/test_api_app_parity.py` (passes)
  - `npm run build` (passes)

No blocking issues remain for Phase 25d implementation.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 3
STATE: approved
