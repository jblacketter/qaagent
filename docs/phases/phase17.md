# Phase 17: Wire Documentation into Web UI Analysis Pipeline

## Status
- [x] Planning
- [ ] In Review
- [ ] Approved
- [ ] Implementation
- [ ] Implementation Review
- [ ] Complete

## Roles
- Lead: claude
- Reviewer: codex
- Arbiter: Human

## Summary
**What:** Connect the existing doc generation engine to the web UI analysis pipeline so that documentation is automatically generated when a repository is analyzed, and the App Docs page displays repo-specific documentation instead of stale/missing data.
**Why:** The doc engine (Phase 6) is fully functional via CLI (`qaagent doc generate`) and has a complete React UI (`/doc` with features, integrations, CUJs, architecture diagrams), but the two are not connected through the web UI analysis flow. Users who add a repository and run analysis see an empty or stale App Docs page.
**Depends on:** Phase 6 (App Documentation) - Complete

## Context

Current state observed by the user:
- Adding a GitHub repo (e.g., `https://github.com/spherop/sonicgrid`) and running analysis produces route discovery, risk assessment, and test generation — but **no documentation**.
- Visiting `/doc` shows "X Documentation" with 0 routes, 0 features, 17 integrations — this is stale data from a previous unrelated run loaded via `load_active_profile()`.
- The doc API (`/api/doc`) calls `_get_doc()` which uses `load_active_profile()` to find `project_root`, then loads `.qaagent/appdoc.json`. This is not repo-aware — it uses a single global active target.
- The React doc page is feature-complete: it has feature cards, integration cards, CUJ list, architecture diagrams (React Flow), markdown export, and a regenerate button.
- The `generate_documentation()` function accepts a `routes` parameter to skip redundant route re-discovery.

## Scope

### In Scope
1. **Add doc generation to the analysis pipeline** — After route discovery and other analysis steps, run documentation generation for the analyzed repo.
2. **Make doc API repo-aware** — Doc endpoints should accept a `repo_id` parameter and load/save documentation per-repository rather than relying on global active target.
3. **Reuse discovered routes** — Pass the already-discovered `routes.json` to the doc generator to avoid redundant discovery.
4. **Fix app_name** — Use the repository name from the repo record instead of falling back to "Application" or stale config.
5. **Connect React UI to repo context** — The App Docs sidebar link and page should be scoped to the currently-selected repository.

### Out of Scope
- LLM-powered prose synthesis improvements (existing prose synthesis is adequate).
- New doc engine analysis capabilities (CUJ patterns, integration detection improvements).
- Doc engine configuration via `.qaagent.yaml` (works today via CLI, not needed for web UI MVP).
- Markdown export improvements or new export formats.

## Technical Approach

### P1 — Add Doc Generation to Analysis Pipeline

**File:** `src/qaagent/api/routes/repositories.py`

After the existing analysis commands (route discovery, collectors, risks, test generation), add a doc generation step:

1. After route discovery produces `routes.json`, load the discovered routes.
2. Call `generate_documentation()` directly (Python, not subprocess) with:
   - `source_dir` = repo path
   - `app_name` = repo name
   - `routes` = pre-discovered routes (avoids re-discovery)
   - `use_llm` = False (fast, no external dependency for pipeline)
3. Call `save_documentation()` with the repo path as `project_root`.
4. This produces `.qaagent/appdoc.json` inside the repo directory.

This step should always run (not gated behind an option checkbox) since documentation is a core output.

### P2 — Make Doc API Repo-Aware

**File:** `src/qaagent/api/routes/doc.py`

Current `_get_doc()` uses `load_active_profile()` → global target. Change to accept a repo context:

1. **Add a shared `_resolve_project_root(repo_id)` helper** at module level in `doc.py`:
   - If `repo_id` is provided and found in the `repositories` dict → return `Path(repo.path)`.
   - If `repo_id` is provided but **not found** → raise `HTTPException(404, detail=f"Repository '{repo_id}' not found")`. **Do not silently fall back.**
   - If `repo_id` is `None` (omitted) → use existing fallback: `load_active_profile()` → `Path.cwd()`.
2. Refactor `_get_doc()` to accept an optional `repo_id` parameter and call `_resolve_project_root(repo_id)` instead of inlining the profile lookup.
3. Add `repo_id: Optional[str] = None` as a **query parameter** to all doc GET endpoints (`/doc`, `/doc/features`, `/doc/features/{feature_id}`, `/doc/integrations`, `/doc/cujs`, `/doc/architecture`, `/doc/export/markdown`).
4. Add `repo_id: Optional[str] = None` as a query parameter to the `POST /doc/regenerate` endpoint. When provided, use `_resolve_project_root(repo_id)` for both `source_dir` and `save_documentation(project_root=...)`.
5. All endpoints call the same `_resolve_project_root` — no duplicated resolution logic.

### P3 — Connect React UI to Repo Context

**Files:**
- `src/qaagent/dashboard/frontend/src/services/api.ts`
- `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx`
- `src/qaagent/dashboard/frontend/src/pages/FeatureDetail.tsx`
- `src/qaagent/dashboard/frontend/src/pages/Integrations.tsx`
- `src/qaagent/dashboard/frontend/src/pages/Architecture.tsx`
- `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx`

**Canonical repo context approach: `?repo=<repo_id>` URL search parameter.**

1. **All doc pages read `repo` from `useSearchParams()`** (React Router). The `repo` search parameter is the single source of truth for which repository's documentation is being viewed.
2. **All navigation to doc pages preserves the `?repo=` parameter:**
   - Sidebar "App Docs" link: `/doc?repo=<repo_id>` (using the currently-active repo from the repositories list or URL context).
   - Feature card links: `/doc/features/<id>?repo=<repo_id>`.
   - Integrations link: `/doc/integrations?repo=<repo_id>`.
   - Architecture link: `/doc/architecture?repo=<repo_id>`.
   - Breadcrumb/back links preserve `?repo=`.
3. **API client methods accept an optional `repoId` parameter** and append `?repo_id=<value>` to all doc endpoint calls. Example: `getAppDoc(repoId?: string)`.
4. **React Query keys include `repoId`** to prevent cross-repo cache bleed. Example: `queryKey: ["appDoc", repoId]`, `queryKey: ["features", repoId]`, etc. When `repoId` changes, queries refetch automatically.
5. **No-repo fallback:** If `?repo=` is absent, show an informational prompt: "Select a repository to view its documentation" with a link to `/repositories`. Do not attempt to load documentation without a repo context in the web UI.

### P4 — Route Reuse in Pipeline

**File:** `src/qaagent/api/routes/repositories.py`

After the `qaagent analyze routes --source . --out routes.json` command completes:

1. Load `routes.json` from the repo directory.
2. Parse routes into `Route` objects using the existing route model.
3. Pass these to `generate_documentation(routes=routes, ...)`.

This avoids the doc generator re-running route discovery (which would duplicate the ~15s route scan).

### P5 — Validation & Polish

**Contract tests for repo-aware doc API** (new test file: `tests/api/test_doc_repo_aware.py`):

1. `GET /api/doc?repo_id=<valid>` → 200, returns documentation scoped to that repo (verify `app_name` matches repo name).
2. `GET /api/doc?repo_id=<invalid>` → 404 with `"Repository '<id>' not found"` detail.
3. `GET /api/doc` (no `repo_id`) → existing fallback behavior (200 if active profile has docs, 404 otherwise).
4. `POST /api/doc/regenerate` with `repo_id=<valid>` → 200, regenerated doc has correct `source_dir`.
5. `POST /api/doc/regenerate` with `repo_id=<invalid>` → 404.

**Integration test** (in `tests/integration/` or extending existing):

6. End-to-end: create repo → analyze → verify `GET /api/doc?repo_id=X` returns documentation with `total_routes > 0` and non-empty features list.

**Regression:**

7. Verify existing 179 doc tests still pass (`pytest tests/doc/`).
8. Manual smoke test: add a GitHub repo in the web UI, run analysis, navigate to App Docs, verify features/integrations/CUJs populate correctly with repo-specific data.

## Files to Create/Modify

### New Files
- `docs/phases/phase17_impl.md` (implementation phase)
- `tests/api/test_doc_repo_aware.py` — Contract tests for repo-aware doc API endpoints

### Modified Files
- `src/qaagent/api/routes/repositories.py` — Add doc generation step to analysis pipeline
- `src/qaagent/api/routes/doc.py` — Add `repo_id` query parameter, make repo-aware
- `src/qaagent/dashboard/frontend/src/services/api.ts` — Pass repo_id to doc endpoints
- `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx` — Use repo context
- `src/qaagent/dashboard/frontend/src/pages/FeatureDetail.tsx` — Use repo context
- `src/qaagent/dashboard/frontend/src/pages/Integrations.tsx` — Use repo context
- `src/qaagent/dashboard/frontend/src/pages/Architecture.tsx` — Use repo context
- `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx` — Scope App Docs link to repo

## Success Criteria
- [ ] Analyzing a repository in the web UI automatically generates documentation
- [ ] `/api/doc?repo_id=X` returns documentation scoped to repository X
- [ ] `/api/doc?repo_id=<invalid>` returns 404 (no silent fallback)
- [ ] `/api/doc` (no repo_id) preserves existing fallback behavior
- [ ] App Docs page (`/doc?repo=X`) displays correct app name, routes, features, integrations for repo X
- [ ] Route discovery is not duplicated (doc generator reuses `routes.json`)
- [ ] Existing doc tests (179 tests) continue to pass
- [ ] Contract tests for repo-aware endpoints pass (5 test cases in `test_doc_repo_aware.py`)
- [ ] Regenerate button on App Docs page works for the selected repo
- [ ] All doc page navigation preserves `?repo=` context
- [ ] React Query keys include `repoId` — no cross-repo cache bleed
- [ ] Graceful fallback when no repo is selected (prompt to select one)

## Resolved Decisions
- Doc generation runs automatically as part of analysis (not gated behind a checkbox) — documentation is a core output, not optional.
- Use `use_llm=False` in the pipeline for speed and reliability; users can regenerate with LLM via the Regenerate button.
- Keep backward compatibility for CLI users by falling back to `load_active_profile()` when no `repo_id` is provided.
- **Repo context in React UI uses `?repo=<repo_id>` URL search parameter** as the single canonical approach (not app state or React context). All doc links preserve this parameter.
- **Backend repo resolution: explicit `_resolve_project_root(repo_id)` helper.** When `repo_id` is provided but unknown, return 404 — never silently fall back to a different repo.
- **React Query cache keys include `repoId`** to prevent stale cross-repo data.

## Risks
- Route model serialization: `routes.json` (produced by CLI `analyze routes`) must be compatible with the `Route` model expected by `generate_documentation()`. Mitigated by using the same `Route` model for both.
- In-memory repository storage: The `repositories` dict is ephemeral (lost on server restart). This is a pre-existing limitation, not introduced by this phase. A future phase should add persistent storage.
- React build required: Frontend changes require `npm run build` to take effect. Documented in development workflow.
