# Phase 8: Parallel Test Execution

## Context

`RunOrchestrator.run_all()` currently executes test suites sequentially — unit, then behave, then e2e — each blocking until complete. Total wall time = T_unit + T_behave + T_e2e. Since suites are completely independent (no data dependencies, isolated output directories, separate subprocesses), they can run concurrently to reduce wall time to max(T_unit, T_behave, T_e2e).

## Scope

### In Scope
- `RunSettings.parallel` config flag (default: `false`, backward compatible)
- `RunSettings.max_workers` config (default: number of enabled suites)
- `RunOrchestrator` refactor: extract per-suite logic, add parallel path using `ThreadPoolExecutor`
- CLI `--parallel` flag on `run-all` command
- Thread safety by design: defer evidence writing to after parallel execution
- Tests for parallel behavior

### Out of Scope
- Intra-suite parallelism (e.g., running pytest with `-n auto`) — that's pytest-xdist, not orchestrator
- Per-suite log buffering / pretty output — acceptable for V1 to have interleaved logs
- Process pool (overkill for 3 subprocess-based suites)

## Technical Approach

### Thread Safety by Structure

Instead of adding locks to `RunHandle`/`EvidenceWriter`, defer all evidence writes to after parallel execution completes. During parallel phase, only `runner.run()` executes (isolated subprocess + output dir per suite). After all futures resolve, aggregate results and write evidence sequentially.

| Component | During Parallel | After Parallel |
|-----------|----------------|----------------|
| `runner.run()` | Yes (thread-safe: isolated subprocess) | — |
| `_retry_failed()` | Yes (same isolation) | — |
| `_write_test_records()` | — | Yes (sequential) |
| `_collect_artifacts()` | — | Yes (sequential) |
| `handle.increment_count()` | — | Yes (sequential) |
| `handle.finalize()` | — | Yes (sequential) |

**No locks needed.** Thread safety achieved by structure, not synchronization.

## Implementation Plan

### Step 1: Config — `RunSettings` (+4 lines)

**`src/qaagent/config/models.py`** (lines 92-99)

Add to `RunSettings`:
```python
parallel: bool = Field(default=False, description="Run suites concurrently")
max_workers: Optional[int] = Field(default=None, description="Max concurrent suites (defaults to number of enabled suites)")
```

### Step 2: Orchestrator Refactor (~+40 net lines)

**`src/qaagent/runners/orchestrator.py`**

1. **New imports**: `concurrent.futures.ThreadPoolExecutor`

2. **Extract `_run_single_suite()`** from the `run_all` loop body (lines 95-122):
   - Takes `suite_name`, `generated`, `base_url`
   - Returns `Optional[Tuple[str, TestResult]]` (None if skipped)
   - Handles: enabled check, path resolution, `run_suite()`, retry

3. **Add `_run_suites_sequential()`**: wraps existing loop using `_run_single_suite`

4. **Add `_run_suites_parallel()`**: submits all enabled suites to `ThreadPoolExecutor`, collects futures, reorders results to `suite_order`. Exception in one suite captured as `errors=1` TestResult, doesn't crash others.

5. **Refactor `run_all()`**: branch on `self.run_settings.parallel`, then aggregate + write evidence sequentially from either path.

### Step 3: CLI Flag (+6 lines)

**`src/qaagent/commands/run_cmd.py`**

Add `--parallel` and `--max-workers` options to `run_all` command. CLI flags override config's `run.parallel` / `run.max_workers`. Display "Running suites in parallel..." or "sequentially..." accordingly.

### Step 4: Tests (~+120 lines)

**`tests/unit/runners/test_orchestrator.py`** (extend existing, ~+100 lines):
- `TestRunSettingsParallel` — config defaults, YAML parsing
- `TestParallelExecution` — all suites run, results in suite_order, one failure doesn't crash others, exception captured, evidence written correctly, max_workers respected, retry works in parallel mode
- Existing sequential tests remain unchanged (regression guard)

**`tests/integration/commands/test_run_cmd.py`** (extend, ~+20 lines):
- `--parallel` flag accepted and sets config

## Files Summary

| Action | File | Delta |
|--------|------|-------|
| Modify | `src/qaagent/config/models.py` | +4 lines |
| Modify | `src/qaagent/runners/orchestrator.py` | +55 new, -15 refactored, net +40 |
| Modify | `src/qaagent/commands/run_cmd.py` | +6 lines |
| Modify | `tests/unit/runners/test_orchestrator.py` | +100 lines |
| Modify | `tests/integration/commands/test_run_cmd.py` | +20 lines |

**No new files. No new dependencies.** Total: ~+170 lines across 5 files.

## Success Criteria

- [ ] `parallel: false` (default) preserves exact current sequential behavior
- [ ] `parallel: true` executes all enabled suites concurrently via ThreadPoolExecutor
- [ ] Results are reported in `suite_order` regardless of completion order
- [ ] One suite failure does not prevent other suites from completing
- [ ] Exception in a runner is captured as `errors=1`, not propagated
- [ ] Evidence (test records, artifacts, manifest) written correctly after parallel execution
- [ ] `max_workers` config limits concurrency
- [ ] `qaagent run-all --parallel` CLI flag works and overrides config
- [ ] Retry logic works correctly in parallel mode
- [ ] All existing orchestrator tests pass unchanged (no regressions)
- [ ] New tests cover parallel happy path, failure isolation, ordering, and config

## Risks

- **Log interleaving**: Parallel suites log concurrently. Acceptable for V1 — stdlib logging is thread-safe, and output remains parseable.
- **Subprocess hangs**: If a subprocess hangs beyond timeout, `run_command()` already catches `TimeoutExpired`. Thread will return error result normally.
- **Shared filesystem**: Each suite writes to isolated `output_dir / suite_name`. No conflict.

## Review Findings (Plan Agent)

### Confirmed Safe
- All three runners (`PytestRunner`, `BehaveRunner`, `PlaywrightRunner`) are thread-safe: `run_suite()` creates a new runner instance per call, each with isolated `output_dir`
- `run_command()` copies `os.environ` fresh each call — thread-safe
- `_resolve_base_url()` is read-only and stateless — safe
- `_resolve_test_path()` only reads the `generated` dict — safe
- `FailureDiagnostics` is stateless and runs after parallel phase — safe
- CLI snapshot tests won't break (they track command names, not options)

### Issues to Address in Implementation
1. **Evidence writes are NOT thread-safe** (confirmed): `Manifest.increment_count()` is non-atomic read-modify-write, `JsonlWriter.append()` could interleave, `handle.write_manifest()` could corrupt JSON. **Plan's deferred-write approach is correct and necessary.**
2. **Retries within threads**: Safe and preferred — runners are stateless instances. Keep retries inside `_run_single_suite()`.
3. **`total_duration` semantics**: In parallel mode, sum of suite durations exceeds wall-clock time. Keep as "total CPU-seconds" for backward compatibility — document this.
4. **CLI `--parallel` precedence**: Use `parallel = cli_parallel or profile.run.parallel`. Avoid mutating the profile — pass as parameter or set before orchestrator construction.
5. **Exception handling in `Future.result()`**: Wrap in try/except, convert to error `TestResult(errors=1)`.
6. **Add `--max-workers` CLI flag** to match `RunSettings.max_workers`.
7. **Logging**: Stdlib logging is thread-safe. Interleaved output is acceptable for V1.
