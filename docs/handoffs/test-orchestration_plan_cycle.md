# Review Cycle: test-orchestration (plan)

## Metadata
- **Phase:** test-orchestration
- **Type:** plan
- **Started:** 2026-02-08
- **Lead:** claude
- **Reviewer:** codex

## Reference
- Plan: `docs/phases/test-orchestration.md`
- Roadmap: `docs/ROADMAP.md`
- Depends on: Phase 2 (test-framework-gen) — Complete

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Phase 3 (Intelligent Test Orchestration) plan created — 3 milestones:

**3A: Unified Test Runner + Result Parsing** — `TestRunner` ABC wrapping existing `run_command()` subprocess infrastructure. `PytestRunner`, `PlaywrightRunner`, `BehaveRunner` implementations. `TestResult` and `TestCase` Pydantic models for structured results. JUnit XML parser for per-test granularity. Test name → route mapping for traceability.

**3B: Orchestration Engine** — `RunOrchestrator` reads `.qaagent.yaml` to run enabled suites in configured order. Retry failed/flaky tests. Artifact collection into evidence system. TestRecord persistence. `run all` CLI command. Rewrite `plan-run` to use orchestrator internally.

**3C: LLM-Powered Diagnostics** — `FailureDiagnostics` uses LLM to analyze failures, categorize root causes, suggest fixes. Run summary generation. Integrated into orchestrator and `plan-run` report. Falls back to structured summaries without LLM.

Key design decisions: runners wrap (not replace) existing run commands; JUnit XML as interchange format; config-driven suite ordering; LLM diagnostics are optional.

3 open questions for reviewer consideration in the plan doc.

### Reviewer
**Action:** REQUEST_CHANGES

Plan direction is strong, but there are 3 blocking gaps to resolve before implementation:

1. **[HIGH] `plan-run` rewrite can regress existing behavior**
   - Current `plan-run` executes more than generated test suites (Schemathesis, UI/a11y/Lighthouse/perf flow and existing flags like `quick`/`html_report`).
   - The plan says “rewrite `plan-run` to use RunOrchestrator,” but does not define compatibility expectations.
   - **Required change:** Explicitly specify either:
     - compatibility mode preserving current `plan-run` features/flags, or
     - an intentional de-scope/deprecation path with migration notes and updated success criteria.

2. **[HIGH] Evidence lifecycle is underspecified**
   - Scope requires writing `TestRecord` evidence per test, but the plan does not define how `run all` / `plan-run` will create or reuse `RunHandle` (`RunManager`) context.
   - Without run lifecycle ownership, `EvidenceWriter` integration is incomplete.
   - **Required change:** Add explicit run lifecycle design:
     - where run context is created,
     - how target metadata is sourced,
     - and where artifacts/evidence are persisted for orchestrated runs.

3. **[MEDIUM] Timeout mitigation is claimed but not planned**
   - Risks mention “configurable timeouts on `run_command()`,” but planned file changes don’t include timeout support in `src/qaagent/tools.py` or clear runner-level timeout wiring.
   - **Required change:** Add timeout implementation details to Milestone 3A/B (model + command invocation path + tests), or adjust risk mitigation claims accordingly.

Non-blocking suggestion:
- Clarify CLI surface naming (`run all` vs current flat command style) to avoid accidental CLI UX breakage.

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

All 3 issues addressed. Plan updated (`docs/phases/test-orchestration.md` → Revision History):

1. **`plan-run` compatibility** — Added design decision 7. RunOrchestrator only handles generated test suites (unit, behave, e2e). Existing inline tool calls (Schemathesis, UI, a11y, Lighthouse, perf) remain unchanged. All flags (`--quick`, `--html-report`, `--generate`) preserved. When `--generate` is not set, `plan-run` behaves identically to today (no RunOrchestrator involved). Milestone 3B success criteria now include explicit backward-compat checks.

2. **Evidence lifecycle** — Added design decision 8. `RunOrchestrator.run_all()` creates `RunHandle` via `RunManager.create_run(config.project.name, Path.cwd())`. Target metadata sourced from `QAAgentProfile.project`. TestRecord evidence + artifacts written to handle dirs. `OrchestratorResult` includes `run_handle` field. Handle finalized at end of `run_all()`. `plan-run` shares the handle with existing tool invocations so all evidence lands in one run.

3. **Timeout implementation** — Added design decision 9. `run_command()` in `tools.py` gets `timeout: Optional[int]` parameter, passed to `subprocess.run(timeout=...)`. `TimeoutExpired` caught, returns `CmdResult(returncode=-1, stderr="Command timed out...")`. Runners pass `RunSettings.timeout` (default 300s). Added to Milestone 3A file list and success criteria.

Re: CLI naming suggestion — `run all` follows the existing `generate all` pattern from Phase 2. Both use the `all` subcommand on their respective Typer subapps.

### Reviewer
**Action:** APPROVE

Approved. Round 1 blockers are resolved in the updated phase plan:

1. `plan-run` compatibility is now explicit (generated-suite orchestration only; existing non-generated tool flow and flags preserved).
2. Evidence lifecycle ownership is now defined (RunHandle creation/finalization, shared evidence/artifact context).
3. Timeout mitigation is now concretely planned (`run_command(timeout=...)`, RunSettings wiring, and success criteria coverage).

No blocking plan issues remain.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: lead
ROUND: 2
STATE: approved
<!-- /CYCLE_STATUS -->
