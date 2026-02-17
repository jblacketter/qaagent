# Phase 17 Implementation: Wire Documentation into Web UI Analysis Pipeline

## Summary of Changes

### P1+P4 — Doc Generation in Analysis Pipeline with Route Reuse
**File:** `src/qaagent/api/routes/repositories.py`

Added doc generation step after CLI analysis commands complete. Loads routes from `routes.json` (avoiding re-discovery), calls `generate_documentation()` directly in-process with `use_llm=False`, and saves to `.qaagent/appdoc.json` in the repo directory. Wrapped in try/except so doc generation failure doesn't block analysis.

### P2 — Repo-Aware Doc API
**File:** `src/qaagent/api/routes/doc.py`

- Added `_resolve_project_root(repo_id)` shared helper with explicit semantics:
  - `repo_id` provided + found → returns `Path(repo.path)`.
  - `repo_id` provided + not found → raises `HTTPException(404)`.
  - `repo_id` omitted → falls back to `load_active_profile()` / `Path.cwd()`.
- Refactored `_get_doc()` to accept optional `repo_id`.
- Added `repo_id: Optional[str] = Query(None)` to all 8 endpoints (GET `/doc`, `/doc/features`, `/doc/features/{id}`, `/doc/integrations`, `/doc/cujs`, `/doc/architecture`, `/doc/export/markdown`, and POST `/doc/regenerate`).
- `regenerate_doc()` uses `_resolve_project_root` for both source_dir and save path.

### P3 — React UI Repo Context
**Files modified:**
- `src/qaagent/dashboard/frontend/src/services/api.ts` — All doc API methods accept optional `repoId` parameter, appended as `?repo_id=<value>` query string via `_docQuery()` helper.
- `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx` — Reads `?repo=` from `useSearchParams()`. Shows "Select a repository" prompt when no repo. Query key includes `repoId`: `["appDoc", repoId]`.
- `src/qaagent/dashboard/frontend/src/pages/FeatureDetail.tsx` — Reads `?repo=`, passes to API calls. Breadcrumb link preserves `?repo=`. Query keys scoped: `["feature", featureId, repoId]`.
- `src/qaagent/dashboard/frontend/src/pages/Integrations.tsx` — Reads `?repo=`, passes to API. Query key: `["integrations", repoId]`.
- `src/qaagent/dashboard/frontend/src/pages/Architecture.tsx` — Reads `?repo=`, passes to API. Query key: `["architecture", repoId]`.
- `src/qaagent/dashboard/frontend/src/components/Doc/FeatureCard.tsx` — Accepts `repoId` prop, appends `?repo=` to feature detail links.
- `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx` — Reads `?repo=` from URL, appends to `/doc` sidebar link.

### P5 — Contract Tests
**New file:** `tests/api/test_doc_repo_aware.py`

5 contract tests:
1. `GET /api/doc?repo_id=<valid>` → 200, app_name matches repo.
2. `GET /api/doc?repo_id=<invalid>` → 404.
3. `GET /api/doc` (no repo_id) → 404 when no active docs.
4. `POST /api/doc/regenerate?repo_id=<valid>` → 200, correct source_dir.
5. `POST /api/doc/regenerate?repo_id=<invalid>` → 404.

## Validation Results
- 5/5 new contract tests pass
- 179/179 existing doc tests pass (no regressions)
- React frontend builds successfully
