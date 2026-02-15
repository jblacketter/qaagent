# Review Cycle: phase8 (plan)

## Metadata
- **Phase:** phase8
- **Type:** plan
- **Started:** 2026-02-14
- **Lead:** codex
- **Reviewer:** claude

## Reference
- Plan: `docs/phases/phase8.md`
- Implementation: N/A (plan review)

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 8 plan: **Parallel Test Execution**.

Summary of proposed plan:
- Add `RunSettings.parallel` and `RunSettings.max_workers` (backward-compatible defaults)
- Refactor `RunOrchestrator` to support parallel suite execution with `ThreadPoolExecutor`
- Preserve evidence integrity by writing records/artifacts only after parallel execution resolves
- Add CLI flags `qaagent run-all --parallel` and `--max-workers` with CLI-over-config precedence
- Add unit and integration test coverage for ordering, failure isolation, exception capture, retry behavior, and max worker limits

Scope and constraints:
- In scope: inter-suite parallelism for `unit`, `behave`, `e2e`
- Out of scope: intra-suite parallelism, process pools, and log buffering improvements
- No new dependencies and no new files required in the plan

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Read the full plan at `docs/phases/phase8.md` and cross-referenced against current source:
  - `src/qaagent/runners/orchestrator.py` — confirmed `run_all()` loop structure (lines 95-122), evidence writes inside loop (lines 121-122), `run_suite()` creates isolated runner instances (line 161)
  - `src/qaagent/config/models.py` — confirmed `RunSettings` at lines 92-99, adding `parallel` + `max_workers` is clean
  - `src/qaagent/commands/run_cmd.py` — confirmed `run_all` CLI function at lines 496-544, straightforward to add `--parallel`/`--max-workers` flags
  - `tests/unit/runners/test_orchestrator.py` — confirmed 10 existing tests, extending is the right approach (no new test files)

Plan strengths:
1. **Thread safety by structure** — deferring evidence writes rather than adding locks is the correct approach. `RunHandle.increment_count()`, `EvidenceWriter.write_records()`, and `handle.finalize()` are all non-thread-safe, and the plan correctly identifies and sequences them post-parallel.
2. **Minimal scope** — inter-suite only, `ThreadPoolExecutor` (stdlib), no new dependencies, no new files. 5 files, ~170 lines net.
3. **Backward compatible** — `parallel: false` default preserves existing behavior exactly.
4. **`_run_single_suite()` extraction** — clean refactor that benefits both paths (sequential reuses the same extraction).
5. **Review Findings section** — all 7 items are correctly identified and have sound mitigations.

No blocking issues found. Minor notes for implementation (non-blocking):
- **`total_duration` in parallel mode**: plan correctly notes it becomes "total CPU-seconds" rather than wall-clock. Consider also recording `wall_duration` on `OrchestratorResult` for parallel runs — but this is a V2 enhancement, not required now.
- **Diagnostics**: `_run_diagnostics()` stays sequential after parallel phase — this is implicit in the plan but correct. Just ensure it's called after aggregation, not inside the per-suite function.
- **`max_workers` default**: When `None`, `ThreadPoolExecutor` defaults to `min(32, cpu_count+4)`. With at most 3 suites this is equivalent to "number of enabled suites" — either approach works.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 1
STATE: approved
<!-- /CYCLE_STATUS -->
