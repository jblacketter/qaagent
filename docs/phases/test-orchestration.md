# Phase: Intelligent Test Orchestration

## Status
- [x] Planning
- [x] In Review
- [x] Approved
- [x] Implementation
- [x] Implementation Review
- [x] Complete

## Roles
- Lead: claude
- Reviewer: codex
- Arbiter: Human

## Summary
**What:** Close the gap between test generation and test execution. Build a unified test runner abstraction, result parsing, orchestrated execution pipeline, and LLM-powered failure analysis. After this phase, `qaagent plan-run` is a true end-to-end pipeline: discover routes, assess risks, generate tests, run them, parse results, diagnose failures, and produce an actionable report.
**Why:** Phase 2 generates complete test suites, but qaagent can't run them intelligently. The existing `run` commands are standalone CLI wrappers with no result parsing, no feedback loop, and no cross-suite orchestration. Phase 3 turns qaagent from a "test generator" into a "test lifecycle manager."
**Depends on:** Phase 2 (Test Framework Generation) — specifically GenerationResult, BaseGenerator, TestValidator

## Milestones

Phase 3 is split into 3 milestones, each independently valuable and testable.

### Milestone 3A: Unified Test Runner + Result Parsing
Abstract over pytest/playwright/behave execution with a common `TestRunner` interface. Parse JUnit XML and stdout to extract structured test results. Map test results back to routes.

### Milestone 3B: Orchestration Engine
Dependency-aware, configurable pipeline that runs suites in order, handles parallelism within suites, retries flaky tests, and collects artifacts into the evidence system.

### Milestone 3C: LLM-Powered Diagnostics + Feedback Loop
Use the LLM to analyze test failures, suggest fixes, and produce actionable reports. Re-run failed tests after auto-fix attempts.

---

## Scope

### In Scope
1. **TestRunner ABC** — Uniform interface for running pytest, Playwright, and Behave test suites
2. **TestResult model** — Structured test results (pass/fail/error/skip per test, duration, output, mapped route)
3. **JUnit + stdout parsing** — Extract per-test results from JUnit XML and runner output
4. **RunOrchestrator** — Pipeline engine: configure suite order, run suites, collect results
5. **Retry logic** — Re-run failed/flaky tests with configurable max retries
6. **Artifact collection** — Screenshots, traces, JUnit XML, coverage reports into evidence system
7. **LLM failure analysis** — Analyze failures, infer root cause, suggest code fixes
8. **Enhanced `plan-run`** — Rewrite to use RunOrchestrator for the full pipeline
9. **`run all` command** — Run all enabled test suites via orchestrator
10. **Test-to-route traceability** — Map test results back to discovered routes for coverage reporting

### Out of Scope
- CI/CD template generation (Phase 4)
- Adaptive test selection based on git diff (future)
- Distributed/remote test execution
- Visual regression testing
- Custom test runner plugins

## Technical Approach

### Design Decisions

1. **TestRunner wraps existing `run_cmd` functions.** Each runner delegates to the proven `run_command()` subprocess wrapper. Runners add result parsing on top. Existing CLI commands stay unchanged.

2. **TestResult is a Pydantic model.** Structured, serializable, mappable to routes. Includes per-test granularity (not just suite-level pass/fail).

3. **JUnit XML is the interchange format.** All runners produce JUnit XML (pytest natively, Playwright via reporter, Behave via formatter). A single parser handles all three.

4. **RunOrchestrator is config-driven.** Reads `.qaagent.yaml` to determine which suites to run, in what order, with what parallelism. No hardcoded pipeline.

5. **LLM diagnostics are optional.** Failure analysis requires LLM. Without it, raw test output is still collected and reported. Fallback: structured error summaries without LLM.

6. **Evidence integration reuses RunHandle.** Test results, artifacts, and diagnostics are written into the existing evidence system via EvidenceWriter.

7. **`plan-run` compatibility mode.** The existing `plan-run` behavior (Schemathesis, UI, a11y, Lighthouse, perf, `--quick`, `--html-report`, `--generate`) is preserved exactly. RunOrchestrator handles the *generated test suite* execution (unit, behave, e2e). The existing non-generated runners (Schemathesis, a11y, Lighthouse, perf) remain as inline calls in `plan-run` — they are not managed by RunOrchestrator because they don't produce generated test code, they are standalone tool invocations. The `--generate` flag triggers: generate → RunOrchestrator.run_all() → existing tool runs → report. No flags are removed or changed.

8. **Evidence run lifecycle.** RunOrchestrator creates a `RunHandle` via `RunManager.create_run()` at the start of `run_all()`. Target metadata is sourced from `QAAgentProfile.project` (name, type) and `Path.cwd()`. All test results (TestRecord per case), artifacts (JUnit XML, screenshots, traces), and diagnostics are written into the RunHandle's `evidence_dir` and `artifacts_dir`. The RunHandle is finalized at the end of `run_all()` with a complete manifest. `plan-run` passes the same RunHandle to its existing tool invocations so all evidence lands in one run.

9. **Configurable timeouts via `run_command()`.** Add an optional `timeout: Optional[int]` parameter to `run_command()` in `tools.py`, passed through to `subprocess.run(timeout=...)`. Runners pass per-suite timeouts from `RunSettings.timeout` (default: 300s). On timeout, `subprocess.TimeoutExpired` is caught and returned as a `TestResult` with `returncode=-1` and an error message.

## Milestones — Detailed

### Milestone 3A: Unified Test Runner + Result Parsing

#### Files to Create

1. **`src/qaagent/runners/__init__.py`** — Package init, exports
2. **`src/qaagent/runners/base.py`** — `TestRunner` ABC + `TestResult` + `TestCase` models
   ```python
   class TestCase(BaseModel):
       name: str
       status: Literal["passed", "failed", "error", "skipped"]
       duration: float  # seconds
       output: Optional[str]  # stdout/stderr on failure
       error_message: Optional[str]
       route: Optional[str]  # mapped route path if known

   class TestResult(BaseModel):
       suite_name: str
       runner: str  # "pytest", "playwright", "behave"
       passed: int
       failed: int
       errors: int
       skipped: int
       duration: float
       cases: List[TestCase]
       artifacts: Dict[str, Path]  # junit, coverage, screenshots, etc.
       returncode: int

   class TestRunner(ABC):
       def __init__(self, suite_settings: SuiteSettings, base_url: str, output_dir: Path): ...
       @abstractmethod
       def run(self, test_path: Path, **kwargs) -> TestResult: ...
       @abstractmethod
       def parse_results(self, junit_path: Path, stdout: str) -> TestResult: ...
   ```

3. **`src/qaagent/runners/pytest_runner.py`** — `PytestRunner(TestRunner)`
   - Wraps `run_command(["python", "-m", "pytest", ...])` with JUnit output
   - Parses JUnit XML for per-test results
   - Extracts route from test name convention (`test_get_pets_pet_id_success` → `GET /pets/{pet_id}`)

4. **`src/qaagent/runners/playwright_runner.py`** — `PlaywrightRunner(TestRunner)`
   - Wraps `run_command(["npx", "playwright", "test", ...])` with JUnit reporter
   - Installs deps if needed (`npx playwright install --with-deps`)
   - Collects screenshots, traces, video artifacts
   - Runs `npm install` if `node_modules/` missing

5. **`src/qaagent/runners/behave_runner.py`** — `BehaveRunner(TestRunner)`
   - Wraps `run_command(["python", "-m", "behave", ...])` with JUnit output
   - Parses JUnit XML for scenario-level results

6. **`src/qaagent/runners/junit_parser.py`** — Standalone JUnit XML parser
   - Reuse/refactor existing `report.py:parse_junit()` into a more granular parser
   - Returns `List[TestCase]` with per-test status, duration, output

7. **`tests/unit/runners/test_base.py`** — TestResult, TestCase model tests
8. **`tests/unit/runners/test_pytest_runner.py`** — PytestRunner with mocked subprocess
9. **`tests/unit/runners/test_playwright_runner.py`** — PlaywrightRunner with mocked subprocess
10. **`tests/unit/runners/test_junit_parser.py`** — JUnit parsing from sample XML files
11. **`tests/fixtures/junit/`** — Sample JUnit XML files for each runner type

#### Files to Modify
- `src/qaagent/config/models.py` — Add `RunSettings` with `retry_count: int = 0`, `timeout: int = 300` (seconds), `suite_order: List[str] = ["unit", "behave", "e2e"]`
- `src/qaagent/tools.py` — Add `timeout: Optional[int] = None` parameter to `run_command()`, passed to `subprocess.run(timeout=...)`. Catch `subprocess.TimeoutExpired` and return `CmdResult(returncode=-1, stdout="", stderr="Command timed out after {timeout}s")`

#### Success Criteria
- [ ] `PytestRunner.run()` executes pytest and returns structured `TestResult`
- [ ] `PlaywrightRunner.run()` executes Playwright and returns structured `TestResult`
- [ ] `BehaveRunner.run()` executes Behave and returns structured `TestResult`
- [ ] JUnit parser extracts per-test pass/fail/error/skip with duration and output
- [ ] Test name → route mapping works for generated tests
- [ ] All runners handle missing tools gracefully (error result, not crash)
- [ ] `run_command()` supports configurable timeout and returns error CmdResult on timeout
- [ ] Runners pass `RunSettings.timeout` to `run_command()`

---

### Milestone 3B: Orchestration Engine

#### Files to Create

12. **`src/qaagent/runners/orchestrator.py`** — `RunOrchestrator`
    ```python
    class RunOrchestrator:
        def __init__(self, config: QAAgentProfile, output_dir: Path, llm_settings: Optional[LLMSettings]): ...

        def run_all(self, generated: Optional[Dict[str, GenerationResult]] = None) -> OrchestratorResult: ...
        def run_suite(self, suite_name: str, test_path: Path) -> TestResult: ...
        def retry_failed(self, result: TestResult, max_retries: int = 2) -> TestResult: ...

    class OrchestratorResult(BaseModel):
        suites: Dict[str, TestResult]
        total_passed: int
        total_failed: int
        total_duration: float
        artifacts: Dict[str, Path]
        run_handle: Optional[RunHandle]  # evidence run context
    ```
    - Creates `RunHandle` via `RunManager.create_run(config.project.name, Path.cwd())` at start
    - Reads suite order from `config.run.suite_order` (default: unit → behave → e2e)
    - Runs each enabled suite via the appropriate TestRunner
    - Retries failed tests per `config.run.retry_count`
    - Writes `TestRecord` evidence per test case via `EvidenceWriter`
    - Copies artifacts (JUnit XML, screenshots, traces) into `handle.artifacts_dir`
    - Calls `handle.finalize()` at the end to persist manifest

13. **`tests/unit/runners/test_orchestrator.py`** — Orchestrator with mocked runners

#### Files to Modify

14. **`src/qaagent/commands/run_cmd.py`** — Add `run all` command using RunOrchestrator
15. **`src/qaagent/commands/report_cmd.py`** — Update `plan-run` to use RunOrchestrator for generated test execution only. Preserves all existing behavior:
    - `--quick`, `--html-report`, `--generate` flags unchanged
    - Schemathesis, UI, a11y, Lighthouse, perf inline calls preserved
    - When `--generate` is set: generate → `RunOrchestrator.run_all()` for generated suites → existing tool runs → report
    - When `--generate` is not set: existing behavior exactly as-is (no RunOrchestrator involved)
    - RunOrchestrator's `RunHandle` is passed to existing tool runs so all evidence lands in one run
16. **`src/qaagent/evidence/models.py`** — Ensure `TestRecord` has fields for runner results (suite_name, runner_type, status, duration, route)

#### Success Criteria
- [ ] `RunOrchestrator.run_all()` executes all enabled suites in configured order
- [ ] `RunOrchestrator.run_all()` creates a `RunHandle` and writes evidence/artifacts
- [ ] `run all` CLI command works end-to-end
- [ ] Failed tests are retried up to configured max
- [ ] `plan-run --generate` uses RunOrchestrator for generated suites
- [ ] `plan-run` without `--generate` behaves identically to current behavior (no regression)
- [ ] `plan-run` flags `--quick`, `--html-report` still work as before
- [ ] Artifacts (JUnit, screenshots, traces) are collected into evidence directory
- [ ] TestRecord evidence is written for each test execution

---

### Milestone 3C: LLM-Powered Diagnostics + Feedback Loop

#### Files to Create

17. **`src/qaagent/runners/diagnostics.py`** — `FailureDiagnostics`
    ```python
    class FailureDiagnostics:
        def __init__(self, llm_settings: LLMSettings): ...

        def analyze_failure(self, case: TestCase, test_code: str) -> DiagnosticResult: ...
        def suggest_fix(self, case: TestCase, test_code: str) -> Optional[str]: ...
        def summarize_run(self, result: OrchestratorResult) -> str: ...

    class DiagnosticResult(BaseModel):
        root_cause: str
        category: str  # "assertion", "timeout", "connection", "auth", "data", "flaky"
        suggestion: str
        confidence: float
        fix_code: Optional[str]
    ```
    - Uses LLM to analyze test failure output + test code
    - Categorizes failures (assertion mismatch, timeout, connection refused, auth failure, etc.)
    - Suggests specific code fixes for generated tests
    - Produces a human-readable run summary

18. **`tests/unit/runners/test_diagnostics.py`** — Diagnostics with mocked LLM

#### Files to Modify

19. **`src/qaagent/runners/orchestrator.py`** — Integrate diagnostics into `run_all()` flow
20. **`src/qaagent/commands/report_cmd.py`** — Include diagnostic results in `plan-run` report output

#### Success Criteria
- [ ] `FailureDiagnostics.analyze_failure()` returns categorized root cause with LLM
- [ ] `FailureDiagnostics.summarize_run()` produces readable run summary
- [ ] Diagnostics fall back to structured error summary without LLM
- [ ] `plan-run` report includes failure analysis section when LLM enabled
- [ ] No regressions in existing tests

---

## Risks

- **Subprocess reliability:** Test runners may hang. Mitigated by adding `timeout` parameter to `run_command()` in `tools.py` (Milestone 3A). Runners pass `RunSettings.timeout` (default 300s). On `TimeoutExpired`, returns error `CmdResult`.
- **`plan-run` regression:** Existing `plan-run` behavior must not break. Mitigated by compatibility mode (design decision 7): RunOrchestrator only handles generated suites, existing tool calls remain inline. Success criteria include explicit backward-compat checks.
- **JUnit format variations:** Playwright and Behave JUnit output may differ from pytest. Mitigated by per-runner parse methods + fixture-based tests with sample XML per runner type.
- **LLM diagnostic accuracy:** Failure analysis may be wrong. Mitigated by confidence scores and "suggestion" framing (not authoritative).
- **Node.js dependency:** PlaywrightRunner requires Node.js + npm. Mitigated by graceful degradation (skip with warning).
- **Test isolation:** Running generated tests against real APIs requires a running target. Document this requirement; don't try to mock it.

## Open Questions

1. Should `run all` support parallel suite execution (e.g., unit + behave in parallel, then e2e)? Or always sequential?
2. Should the orchestrator auto-detect generated test paths from GenerationResult, or require explicit paths?
3. Should failure diagnostics attempt auto-fix and re-run, or just report suggestions?

---

## Revision History

### Round 1 Feedback (codex, 2026-02-08)

**Verdict:** REQUEST CHANGES — 3 issues identified.

1. **[HIGH] `plan-run` rewrite can regress existing behavior** — Resolved: Added design decision 7 (compatibility mode). RunOrchestrator only handles generated suites. Existing tool calls (Schemathesis, a11y, Lighthouse, perf) remain inline. All flags preserved. Milestone 3B success criteria updated with explicit backward-compat checks.

2. **[HIGH] Evidence lifecycle is underspecified** — Resolved: Added design decision 8. RunOrchestrator creates `RunHandle` via `RunManager.create_run()` at start of `run_all()`. Target metadata from `QAAgentProfile.project`. All evidence/artifacts written to handle dirs. Handle finalized at end. `OrchestratorResult` includes `run_handle` field. `plan-run` shares the handle with its existing tool calls.

3. **[MEDIUM] Timeout mitigation is claimed but not planned** — Resolved: Added design decision 9. `run_command()` in `tools.py` gets `timeout: Optional[int]` param. Runners pass `RunSettings.timeout`. `TimeoutExpired` caught and returned as error CmdResult. Milestone 3A file list and success criteria updated.
