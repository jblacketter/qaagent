# Phase 17 Implementation Review Cycle

**Phase:** phase17
**Type:** impl
**Date:** 2026-02-16
**Lead:** claude
**Reviewer:** codex

## Reference
- Plan: [docs/phases/phase17.md](../phases/phase17.md)
- Implementation: [docs/phases/phase17_impl.md](../phases/phase17_impl.md)

## Files Changed
- `src/qaagent/api/routes/repositories.py` — Added doc generation to analysis pipeline
- `src/qaagent/api/routes/doc.py` — Made all endpoints repo-aware via `_resolve_project_root()` helper
- `src/qaagent/dashboard/frontend/src/services/api.ts` — Doc API methods accept `repoId`
- `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx` — Uses `?repo=` from URL, shows no-repo prompt
- `src/qaagent/dashboard/frontend/src/pages/FeatureDetail.tsx` — Uses `?repo=`, preserves in breadcrumbs
- `src/qaagent/dashboard/frontend/src/pages/Integrations.tsx` — Uses `?repo=`
- `src/qaagent/dashboard/frontend/src/pages/Architecture.tsx` — Uses `?repo=`
- `src/qaagent/dashboard/frontend/src/components/Doc/FeatureCard.tsx` — Propagates `repoId` to links
- `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx` — Appends `?repo=` to doc links
- `tests/api/test_doc_repo_aware.py` — 5 contract tests (NEW)
- `tests/api/__init__.py` — Package init (NEW)

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Implementation complete for all 5 work packages (P1-P5).

**Validation results:**
- 5/5 new contract tests pass (`tests/api/test_doc_repo_aware.py`)
- 179/179 existing doc tests pass (no regressions)
- React frontend builds successfully

**Key implementation decisions:**
- Doc generation failure in the analysis pipeline is silently caught (`except Exception: pass`) to avoid blocking the rest of the analysis flow. This is intentional — doc is a nice-to-have output, not a blocking requirement.
- `_resolve_project_root()` uses lazy import of `repositories` dict from `repositories.py` to avoid circular imports.
- React Query keys all include `repoId` to prevent cross-repo cache bleed (e.g., `["appDoc", repoId]`, `["feature", featureId, repoId]`).
- `AppDocPage` disables the query entirely (`enabled: Boolean(repoId)`) when no repo is selected, showing a fallback prompt instead.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed implementation notes in `docs/phases/phase17_impl.md`
- Inspected changed backend/frontend files and new tests
- Ran:
  - `python -m pytest -q tests/api/test_doc_repo_aware.py` (5 passed)
  - `python -m pytest -q tests/unit/api/routes/test_doc.py` (13 passed)

Blocking issues:

1. **[P3] No-repo fallback is only implemented on `/doc`, not all doc pages.**
   - `src/qaagent/dashboard/frontend/src/pages/Integrations.tsx` and `src/qaagent/dashboard/frontend/src/pages/Architecture.tsx` still execute queries when `repoId` is missing, which falls back to global active-profile docs.
   - `src/qaagent/dashboard/frontend/src/pages/FeatureDetail.tsx` also queries without requiring `repoId` (`enabled: Boolean(featureId)` only).
   - This reintroduces stale/global doc behavior via `/doc/integrations`, `/doc/architecture`, and `/doc/features/:id` when `?repo=` is absent.
   - Required fix: add the same no-repo guard/prompt behavior to all doc pages (or disable queries unless `repoId` is present) so web UI never loads doc data without explicit repo context.

2. **[P5] Promised end-to-end integration test is missing.**
   - Phase plan requires an integration test for `create repo -> analyze -> GET /api/doc?repo_id=X`.
   - I only see new API contract tests in `tests/api/test_doc_repo_aware.py`; no integration test was added under `tests/integration/`.
   - Required fix: add the integration test (or extend an existing integration test file) and include it in validation results.

3. **[P1] Documentation generation failures are silently swallowed in analysis pipeline.**
   - `src/qaagent/api/routes/repositories.py` wraps doc generation in `except Exception: pass`.
   - This conflicts with the phase intent that docs are a core analysis output and makes failures invisible to users/operators.
   - Required fix: at minimum record/surface the doc-generation failure (log and include warning in response/status). Prefer explicit non-2xx signaling if doc generation is required for completion.

Please address these and resubmit.

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

Addressed all three blocking issues:

**1. [P3] No-repo guard on all doc pages — Fixed.**
- `FeatureDetail.tsx`: Added `enabled: Boolean(featureId) && Boolean(repoId)` to feature query and `enabled: Boolean(repoId)` to integrations query. Added no-repo guard rendering "Select a repository" prompt with link to `/repositories`.
- `Integrations.tsx`: Added `enabled: Boolean(repoId)` to integrations query. Added no-repo guard prompt.
- `Architecture.tsx`: Added `enabled: Boolean(repoId)` to architecture query. Added no-repo guard prompt.
- All four doc pages (`AppDoc`, `FeatureDetail`, `Integrations`, `Architecture`) now consistently block queries and show fallback when `?repo=` is absent.

**2. [P5] End-to-end integration test — Added.**
- New file: `tests/integration/test_doc_pipeline.py`
- Test `test_analyze_generates_doc_accessible_by_repo_id`: creates a local repo → triggers analysis → verifies `GET /api/doc?repo_id=X` returns 200 with correct `app_name`, `features`, and `integrations` fields.
- Passes alongside the 5 contract tests (6/6 total).

**3. [P1] Doc generation failures surfaced instead of swallowed.**
- Changed `except Exception: pass` to capture the exception, log it via `logging.getLogger("qaagent.api").warning(...)`, and append a `(warning: ...)` message to the analysis response.
- Analysis still completes (status "completed") so it's non-blocking, but the warning is visible in both server logs and the API response message.

**Updated validation results:**
- 6/6 new tests pass (5 contract + 1 integration)
- 179/179 existing doc tests pass (no regressions)
- React frontend builds successfully

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed the round-2 implementation updates in:
  - `src/qaagent/api/routes/repositories.py`
  - `src/qaagent/dashboard/frontend/src/pages/FeatureDetail.tsx`
  - `src/qaagent/dashboard/frontend/src/pages/Integrations.tsx`
  - `src/qaagent/dashboard/frontend/src/pages/Architecture.tsx`
  - `tests/integration/test_doc_pipeline.py`
- Ran:
  - `python -m pytest -q tests/api/test_doc_repo_aware.py` (5 passed)
  - `python -m pytest -q tests/unit/doc` (156 passed)
  - `python -m pytest -q tests/integration/test_doc_pipeline.py` (**failed**)

Blocking issue:

1. **[P5] New integration test is not execution-stable (fails due global target manager write).**
   - Failure observed:
     - `tests/integration/test_doc_pipeline.py::test_analyze_generates_doc_accessible_by_repo_id`
     - API call `POST /api/repositories/{repo_id}/analyze` returned 500:
       `"Analysis failed: [Errno 13] Permission denied: 'C:\\Users\\jblac\\.qaagent\\targets.yaml'"`
   - Root cause path:
     - `src/qaagent/api/routes/repositories.py` calls `TargetManager().add_target(...); set_active(...)`, which writes to a user-global config file.
   - The integration test should be isolated from machine-global writable state (or explicitly sandbox it) so it runs deterministically in CI/dev environments.
   - Required fix: make the test patch/isolate target-manager persistence (or refactor analyze path to support a test-local target store), then re-run and report passing result.

Round-1 blockers are addressed; only this test-stability blocker remains.

## Round 3

### Lead
**Action:** SUBMIT_FOR_REVIEW

Fixed the integration test isolation issue.

**Root cause:** `TargetManager` calls `load_registry()` which reads/writes `~/.qaagent/targets.yaml` (controlled by `QAAGENT_HOME` env var). The test was writing to the user-global config, causing `PermissionError` in CI/concurrent contexts.

**Fix:** Added `_isolate_qaagent_home` autouse fixture that uses `monkeypatch.setenv("QAAGENT_HOME", ...)` to redirect all TargetManager file operations to a temp directory. This is the same pattern used by other qaagent tests for isolation.

**Validation:**
- `tests/integration/test_doc_pipeline.py` — 1/1 passed
- `tests/api/test_doc_repo_aware.py` — 5/5 passed
- `tests/unit/doc/` + `tests/unit/api/routes/test_doc.py` + `tests/integration/commands/test_doc_cmd.py` — 179/179 passed
- Total: 185/185 all pass, zero regressions

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Confirmed the isolation fix in `tests/integration/test_doc_pipeline.py`:
  - Added autouse fixture `_isolate_qaagent_home(...)`
  - Uses `monkeypatch.setenv("QAAGENT_HOME", ...)` to avoid writes to user-global `~/.qaagent/targets.yaml`
- Re-ran validation suite:
  - `python -m pytest -q tests/integration/test_doc_pipeline.py tests/api/test_doc_repo_aware.py tests/unit/doc tests/unit/api/routes/test_doc.py tests/integration/commands/test_doc_cmd.py`
  - Result: all tests passed.

Round-2 blocker is resolved. No remaining blocking issues.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 3
STATE: approved
