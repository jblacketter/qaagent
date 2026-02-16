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

#### Priority 4: CLI Commands (Integration) — COMPLETE (94 tests)
- [x] `tests/integration/commands/test_targets_cmd.py` — 9 tests
- [x] `tests/integration/commands/test_workspace_cmd.py` — 12 tests
- [x] `tests/integration/commands/test_run_cmd.py` — 35 tests
- [x] `tests/integration/commands/test_report_cmd.py` — 17 tests
- [x] `tests/integration/commands/test_misc_cmd.py` — 21 tests

#### Priority 5: API Routes — COMPLETE (47 tests)
- [x] `tests/unit/api/routes/test_evidence.py` — 13 tests
- [x] `tests/unit/api/routes/test_runs.py` — 8 tests
- [x] `tests/unit/api/routes/test_repositories.py` — 18 tests
- [x] `tests/unit/api/routes/test_fix.py` — 8 tests

## Files Created

### Session 1 (P1-P3)
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

### Session 2 (P4-P5)
- `tests/integration/commands/test_targets_cmd.py`
- `tests/integration/commands/test_workspace_cmd.py`
- `tests/integration/commands/test_run_cmd.py`
- `tests/integration/commands/test_report_cmd.py`
- `tests/integration/commands/test_misc_cmd.py`
- `tests/unit/api/routes/test_evidence.py`
- `tests/unit/api/routes/test_runs.py`
- `tests/unit/api/routes/test_repositories.py`
- `tests/unit/api/routes/test_fix.py`

## Files Modified
- Added `__init__.py` to all test directories (fixes namespace collision between `test_validator.py` files)

## Decisions Made
- Patching `httpx.get` and `playwright.sync_api.sync_playwright` directly (not via module attribute) because both are imported inside function bodies
- `RouteSource.OPENAPI` (uppercase) matches the actual enum definition
- `Risk` model takes `route` as `Optional[str]`, not a Route object
- `RepoCache.get_cache_stats` rounds `total_size_mb` — test uses `>= 0` instead of `> 0` for tiny test files
- CLI integration tests use `CliRunner` from Typer (not subprocess) per approved testing strategy
- Commands with lazy local imports (e.g., `run_all` importing `load_active_profile`) require patching at the source module, not the command module
- API route tests use `TestClient` with `create_app()` factory, seeding evidence via `RunManager`/`EvidenceWriter`
- Repositories tests use `autouse=True` fixture to clear in-memory storage between tests

## Issues Encountered
- `sitemap.py` imports httpx lazily inside function — can't patch `qaagent.sitemap.httpx`, must patch `httpx.get` directly
- `a11y.py` imports playwright lazily — same pattern, patch `playwright.sync_api.sync_playwright`
- `RouteSource` enum uses uppercase members (OPENAPI, CODE, etc.) — mismatch with initial test code
- Duplicate `test_validator.py` basenames in `generators/` and `repo/` caused pytest collection error — fixed by adding `__init__.py` to all test directories
- `run_all` command imports `load_active_profile` locally inside the function, so must patch at `qaagent.config.load_active_profile` not `qaagent.commands.run_cmd.load_active_profile`
