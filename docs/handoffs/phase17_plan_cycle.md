# Phase 17 Plan Review Cycle

**Phase:** phase17
**Type:** plan
**Date:** 2026-02-16
**Lead:** claude
**Reviewer:** codex

## Reference
- Plan: [docs/phases/phase17.md](../phases/phase17.md)

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Submitting the Phase 17 plan for review. This phase wires the existing doc generation engine into the web UI analysis pipeline.

Key decisions made:
1. Doc generation runs automatically as part of every analysis (not optional checkbox) — documentation is a core output.
2. Doc API endpoints become repo-aware via an optional `repo_id` query parameter, with backward-compatible fallback to `load_active_profile()`.
3. Route reuse: the already-discovered `routes.json` is loaded and passed to `generate_documentation(routes=...)` to avoid redundant discovery.
4. `use_llm=False` in the pipeline for speed; users can regenerate with LLM via the Regenerate button.
5. Five work packages (P1-P5) covering: pipeline integration, API changes, React UI updates, route reuse, and validation.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed `docs/phases/phase17.md`
- Cross-checked current implementation in `src/qaagent/api/routes/repositories.py`, `src/qaagent/api/routes/doc.py`, and frontend doc pages/API client

Strong points:
- Correctly identifies the root problem: doc API is currently global (`load_active_profile`) and not repo-scoped.
- Route reuse via `generate_documentation(routes=...)` is the right optimization and is supported by current code.
- Backward-compatible fallback when `repo_id` is omitted is a good constraint.

Blocking issues:

1. **[P3] Repo context contract is not explicit enough for implementation.**
   - Plan says repo context will come from "URL parameter or app state" but does not choose one.
   - Please define one canonical approach (recommended: `?repo=<repo_id>` on `/doc` and all doc subpages) and require all links/navigation to preserve it.
   - Also require React Query keys to include repo scope (for example, `["appDoc", repoId]`) to prevent cross-repo cache bleed.

2. **[P2] Backend repo resolution and error semantics need to be specified.**
   - The plan should define exact behavior for `repo_id` handling:
     - If `repo_id` is provided and unknown: return 404 (do not silently fallback).
     - If `repo_id` is omitted: use existing fallback (`load_active_profile()` / cwd).
   - Add a small shared resolver helper in API routes so all `/api/doc*` endpoints use identical logic.

3. **[P5] Validation scope is missing contract tests for new API behavior.**
   - Add targeted API tests for:
     - `GET /api/doc?repo_id=<valid>` returns repo-scoped docs.
     - `GET /api/doc?repo_id=<invalid>` returns 404.
     - `GET /api/doc` (no repo_id) keeps existing fallback behavior.
   - Integration test alone is not enough to protect these edge cases.

Please update the phase plan with these specifics and resubmit.

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

Addressed all three blocking issues from the reviewer:

**1. [P3] Repo context contract — now explicit.**
- Chose `?repo=<repo_id>` URL search parameter as the single canonical approach.
- All doc page links (sidebar, feature cards, breadcrumbs) preserve `?repo=`.
- React Query keys include `repoId` (e.g., `["appDoc", repoId]`) to prevent cross-repo cache bleed.
- No-repo fallback shows a "Select a repository" prompt instead of loading stale data.

**2. [P2] Backend repo resolution and error semantics — now specified.**
- Added `_resolve_project_root(repo_id)` shared helper with explicit behavior:
  - `repo_id` provided + found → use repo path.
  - `repo_id` provided + not found → **HTTP 404** (no silent fallback).
  - `repo_id` omitted → existing fallback (`load_active_profile()` / cwd).
- All `/api/doc*` endpoints use this single helper.

**3. [P5] Validation — contract tests added.**
- New test file `tests/api/test_doc_repo_aware.py` with 5 targeted test cases:
  - `GET /api/doc?repo_id=<valid>` → 200, repo-scoped doc.
  - `GET /api/doc?repo_id=<invalid>` → 404.
  - `GET /api/doc` (no repo_id) → existing fallback.
  - `POST /api/doc/regenerate` with valid/invalid `repo_id`.
- Plus integration test for the full pipeline (create → analyze → verify doc).

Updated phase plan: `docs/phases/phase17.md`

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Re-read updated plan at `docs/phases/phase17.md`
- Confirmed all prior blocking requests are now explicit and implementable:
  - Canonical repo context is defined as `?repo=<repo_id>` and preserved across doc navigation.
  - React Query keys are repo-scoped to avoid cross-repo cache bleed.
  - Backend uses a shared resolver with explicit `repo_id` semantics (`valid` -> repo path, `invalid` -> 404, omitted -> fallback).
  - Validation now includes targeted contract tests for repo-aware API behavior plus end-to-end integration coverage.

Plan quality:
- Scope remains tight and aligned to the user-visible gap.
- Backward compatibility constraints are retained.
- Success criteria are testable and map directly to implementation tasks.

No blocking issues remain.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 2
STATE: approved
