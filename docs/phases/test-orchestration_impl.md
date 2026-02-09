# Implementation Log: Intelligent Test Orchestration

**Started:** 2026-02-08
**Lead:** claude
**Plan:** docs/phases/test-orchestration.md

## Progress

### Milestone 3A: Unified Test Runner + Result Parsing — COMPLETE
- [x] `src/qaagent/runners/__init__.py`
- [x] `src/qaagent/runners/base.py` (TestRunner ABC, TestResult, TestCase)
- [x] `src/qaagent/runners/junit_parser.py`
- [x] `src/qaagent/runners/pytest_runner.py`
- [x] `src/qaagent/runners/playwright_runner.py`
- [x] `src/qaagent/runners/behave_runner.py`
- [x] `src/qaagent/tools.py` (timeout parameter)
- [x] `src/qaagent/config/models.py` (RunSettings)
- [x] `tests/unit/runners/test_base.py`
- [x] `tests/unit/runners/test_junit_parser.py`
- [x] `tests/unit/runners/test_pytest_runner.py`
- [x] `tests/unit/runners/test_playwright_runner.py`
- [x] `tests/fixtures/junit/` (sample XML files)

### Milestone 3B: Orchestration Engine — COMPLETE
- [x] `src/qaagent/runners/orchestrator.py`
- [x] `src/qaagent/commands/run_cmd.py` (`run-all` command)
- [x] `src/qaagent/commands/report_cmd.py` (`plan-run --generate` uses RunOrchestrator)
- [x] `src/qaagent/evidence/models.py` (TestRecord updated with runner fields)
- [x] `tests/unit/runners/test_orchestrator.py` (11 tests)
- [x] `tests/fixtures/cli_snapshots/pre_split_commands.json` (added `run-all`)

### Milestone 3C: LLM-Powered Diagnostics — COMPLETE
- [x] `src/qaagent/runners/diagnostics.py` (FailureDiagnostics, DiagnosticResult, RunDiagnosticSummary)
- [x] `tests/unit/runners/test_diagnostics.py` (14 tests)
- [x] Integrate diagnostics into orchestrator (run_all runs diagnostics on failures)
- [x] Include diagnostics in plan-run report and run-all output

## Files Created
- `src/qaagent/runners/__init__.py`
- `src/qaagent/runners/base.py`
- `src/qaagent/runners/junit_parser.py`
- `src/qaagent/runners/pytest_runner.py`
- `src/qaagent/runners/playwright_runner.py`
- `src/qaagent/runners/behave_runner.py`
- `src/qaagent/runners/orchestrator.py`
- `src/qaagent/runners/diagnostics.py`
- `tests/unit/runners/__init__.py`
- `tests/unit/runners/test_base.py`
- `tests/unit/runners/test_junit_parser.py`
- `tests/unit/runners/test_pytest_runner.py`
- `tests/unit/runners/test_playwright_runner.py`
- `tests/unit/runners/test_orchestrator.py`
- `tests/unit/runners/test_diagnostics.py`
- `tests/fixtures/junit/pytest_sample.xml`
- `tests/fixtures/junit/playwright_sample.xml`
- `tests/fixtures/junit/behave_sample.xml`

## Files Modified
- `src/qaagent/tools.py` — Added `timeout` param to `run_command()`
- `src/qaagent/config/models.py` — Added `RunSettings` class, `run` field on `QAAgentProfile`
- `src/qaagent/commands/run_cmd.py` — Added `run-all` command with diagnostic output
- `src/qaagent/commands/report_cmd.py` — Integrated RunOrchestrator + diagnostics into `plan-run --generate`
- `src/qaagent/evidence/models.py` — Added `suite_name`, `runner_type`, `duration`, `route`, `error_message` to `TestRecord`
- `tests/fixtures/cli_snapshots/pre_split_commands.json` — Added `run-all` to command list

## Decisions Made
- `_RUNNER_MAP` module-level dict maps suite names to runner classes. Tests must patch the dict directly (not the class references) since the dict captures references at import time.
- RunOrchestrator compatibility mode: `plan-run --generate` invokes orchestrator for generated suites, then continues with existing inline tool calls (Schemathesis, a11y, Lighthouse, perf). No existing behavior changed.
- TestRecord gains optional runner fields (suite_name, runner_type, duration, route, error_message) — all optional to preserve backward compat with existing evidence records.
- Heuristic pattern ordering: timeout → connection → auth → data → flaky → assertion. More specific categories checked first to avoid false positives (e.g., "401 unauthorized" should match auth, not assertion).
- Diagnostics are optional: run if failures exist, silently skip on errors. Summary text added to evidence manifest via `handle.add_diagnostic()`.

## Issues Encountered
- `SuiteSettings` requires `output_dir` as a required field — test helpers needed explicit `output_dir=""` for disabled suites
- `TestsSettings.e2e` requires `PlaywrightSuiteSettings` (not `SuiteSettings`) — tests must use the correct subclass
- `_RUNNER_MAP` captures class references at import time, so `@patch("...PytestRunner")` doesn't affect the dict — switched to `patch.dict("..._RUNNER_MAP", ...)` in orchestrator tests
- Heuristic pattern overlap: "expected 200 but got 404" matched both assertion and data categories. Fixed by reordering patterns (specific before general) and using unambiguous test data.

## Review Round 1 Fixes

After codex review (4 issues: 3 HIGH, 1 MEDIUM):

1. **Runner cwd/path duplication (HIGH):** Resolved test paths to absolute with `test_path.resolve()`, set `cwd=None` for directories. Affects `pytest_runner.py` and `behave_runner.py`.
2. **No per-test TestRecord evidence (HIGH):** Added `_write_test_records()` to orchestrator — uses `EvidenceWriter` + `EvidenceIDGenerator` to emit one record per `TestCase`. New test: `test_writes_test_records`.
3. **No shared evidence run in plan-run (HIGH):** Acknowledged limitation; added evidence path display. Inline tools pre-date evidence system; shared context deferred.
4. **Route param mapping (MEDIUM):** `_map_test_to_route()` now detects param suffixes (`id`, `pk`, `slug`, `uuid`) and merges with preceding token into `{param}` placeholders. New tests: `test_nested_route_with_param`, `test_delete_route_with_param`, `test_route_without_param`.

## Review Round 2 Fix

After codex review R2 (1 remaining issue: shared evidence run):

5. **Shared evidence run in plan-run (HIGH):** `RunOrchestrator` now accepts optional `run_handle` param (uses it instead of creating own, skips finalization). `plan_run` creates `RunHandle` early, passes to orchestrator, collects inline tool artifacts into it via `_collect_tool_artifacts()`, registers tools in manifest, finalizes once at end. New test: `test_external_handle_used_and_not_finalized`.

## Test Results
- Milestone 3A: 31 runner tests pass
- Milestone 3B: 42 runner tests pass (11 new orchestrator tests)
- Milestone 3C: 56 runner tests pass (14 new diagnostics tests)
- After R1 fixes: 60 runner tests pass (+4 new tests)
- After R2 fix: 61 runner tests pass (+1 external handle test)
- Full suite: 4 pre-existing failures, 0 new regressions
