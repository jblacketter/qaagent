# Implementation Log: Phase 9 - Coverage Gap Analysis

**Started:** 2026-02-14
**Lead:** codex
**Plan:** `docs/phases/phase9.md`

## Progress

### Session 1 - 2026-02-14
- [x] Build route coverage gap engine in `src/qaagent/analyzers/route_coverage.py`
- [x] Consolidate `report.py` coverage computation to delegate to shared engine
- [x] Add `qaagent analyze coverage-gaps` command in `src/qaagent/commands/analyze_cmd.py`
- [x] Add unit and integration tests for coverage matching, CLI behavior, and report extras

### Implementation details
- Added `route_coverage.py` as the shared coverage engine:
  - canonical `(METHOD, PATH)` normalization
  - OpenAPI + routes-source merging
  - JUnit case extraction support (file/dir inputs)
  - deterministic uncovered route ordering with V1 metadata-only priority
- Updated `summarize_api_coverage()` in `src/qaagent/report.py` to delegate to `build_route_coverage()` (single source of truth)
- Extended report rendering (markdown + html) to display top uncovered priority routes while keeping existing API coverage fields intact
- Added `qaagent analyze coverage-gaps` command with:
  - `--routes-file`, `--openapi`, `--junit`, `--out`, `--markdown`
  - active-profile defaults for OpenAPI path and default JUnit locations
  - summary + top uncovered table output
- Updated CLI parity snapshot for the new analyze subcommand

## Files Created
- `src/qaagent/analyzers/route_coverage.py`
- `tests/unit/analyzers/test_route_coverage.py`
- `tests/integration/commands/test_analyze_cmd.py`

## Files Modified
- `src/qaagent/report.py`
- `src/qaagent/commands/analyze_cmd.py`
- `tests/fixtures/cli_snapshots/pre_split_commands.json`

## Test Results
- `pytest -q tests/unit/analyzers/test_route_coverage.py tests/integration/commands/test_analyze_cmd.py tests/unit/test_report_extras.py tests/integration/test_cli_split_parity.py`
  - 38 tests passed, 0 failures
- `pytest -q tests/unit/test_coverage_summary.py`
  - 1 test passed, 0 failures

## Decisions Made
- Begin with engine-first implementation so both CLI and report paths use one source of truth.
- Keep `summarize_api_coverage()` as a compatibility wrapper over the new engine to preserve existing extras/report consumers.
- Keep priority scoring metadata-only in Phase 9 (no direct dependency on risk outputs), per approved plan.

## Issues Encountered
- None
