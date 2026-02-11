# Implementation Log: Phase 5 — Hardening & Test Coverage

**Started:** 2026-02-10
**Lead:** claude
**Plan:** docs/phases/phase5.md

## Progress

### Session 1 - 2026-02-10

#### Priority 1: Core Infrastructure — COMPLETE (73 tests)
- [x] `tests/unit/runners/test_behave_runner.py` — 8 tests
- [x] `tests/unit/evidence/test_writer.py` — 10 tests
- [x] `tests/unit/test_tools.py` — 13 tests
- [x] `tests/unit/test_autofix.py` — 20 tests
- [x] `tests/unit/test_workspace.py` — 22 tests

#### Priority 2: Configuration & Repo — COMPLETE (74 tests)
- [x] `tests/unit/config/test_detect.py` — 17 tests
- [x] `tests/unit/config/test_templates.py` — 8 tests
- [x] `tests/unit/config/test_legacy.py` — 15 tests
- [x] `tests/unit/repo/test_cache.py` — 13 tests
- [x] `tests/unit/repo/test_validator.py` — 21 tests

#### Priority 3: Utilities — COMPLETE (17 tests)
- [x] `tests/unit/test_sitemap.py` — 5 tests
- [x] `tests/unit/test_a11y.py` — 5 tests
- [x] `tests/unit/test_dashboard.py` — 7 tests

#### Priority 4: CLI Commands (Integration)
- [ ] `tests/integration/commands/test_targets_cmd.py`
- [ ] `tests/integration/commands/test_workspace_cmd.py`
- [ ] `tests/integration/commands/test_run_cmd.py`
- [ ] `tests/integration/commands/test_report_cmd.py`
- [ ] `tests/integration/commands/test_misc_cmd.py`

#### Priority 5: API Routes
- [ ] `tests/unit/api/routes/test_evidence.py`
- [ ] `tests/unit/api/routes/test_runs.py`
- [ ] `tests/unit/api/routes/test_repositories.py`
- [ ] `tests/unit/api/routes/test_fix.py`

## Files Created
- `tests/unit/runners/test_behave_runner.py`
- `tests/unit/evidence/test_writer.py`
- `tests/unit/test_tools.py`
- `tests/unit/test_autofix.py`
- `tests/unit/test_workspace.py`
- `tests/unit/config/test_detect.py`
- `tests/unit/config/test_templates.py`
- `tests/unit/config/test_legacy.py`
- `tests/unit/repo/test_cache.py`
- `tests/unit/repo/test_validator.py`
- `tests/unit/test_sitemap.py`
- `tests/unit/test_a11y.py`
- `tests/unit/test_dashboard.py`

## Files Modified
- (none)

## Decisions Made
- Patching `httpx.get` and `playwright.sync_api.sync_playwright` directly (not via module attribute) because both are imported inside function bodies
- `RouteSource.OPENAPI` (uppercase) matches the actual enum definition
- `Risk` model takes `route` as `Optional[str]`, not a Route object
- `RepoCache.get_cache_stats` rounds `total_size_mb` — test uses `>= 0` instead of `> 0` for tiny test files

## Issues Encountered
- `sitemap.py` imports httpx lazily inside function — can't patch `qaagent.sitemap.httpx`, must patch `httpx.get` directly
- `a11y.py` imports playwright lazily — same pattern, patch `playwright.sync_api.sync_playwright`
- `RouteSource` enum uses uppercase members (OPENAPI, CODE, etc.) — mismatch with initial test code
