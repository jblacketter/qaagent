# Review Cycle: phase9 (plan)

## Metadata
- **Phase:** phase9
- **Type:** plan
- **Started:** 2026-02-14
- **Lead:** codex
- **Reviewer:** claude

## Reference
- Plan: `docs/phases/phase9.md`
- Implementation: N/A (plan review)

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 9 plan: **Coverage Gap Analysis**.

Plan highlights:
- Introduce a dedicated route-coverage gap analyzer to map discovered operations against executed test evidence (JUnit + route hints)
- Add a new CLI entrypoint (`qaagent analyze coverage-gaps`) with JSON/Markdown outputs and active-profile defaults
- Integrate route gap summaries into report extras/markdown/html while preserving backward compatibility when coverage inputs are unavailable
- Add focused unit and integration tests for normalization, matching, CLI behavior, and report rendering

The plan is scoped to route-level gap detection and reporting only. It intentionally excludes code-coverage instrumentation changes and automatic test generation.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Read the full plan at `docs/phases/phase9.md`
- Cross-referenced against existing source:
  - `src/qaagent/report.py` — `summarize_api_coverage()` (lines 802-848), `analyze_extras()` (lines 607-636), `render_markdown()` extras rendering
  - `src/qaagent/openapi_utils.py` — `enumerate_operations()`, `covered_operations_from_junit_case_names()`, `Operation` model
  - `src/qaagent/commands/analyze_cmd.py` — existing analyze subcommands, `analyze_app` Typer group
  - `src/qaagent/analyzers/models.py` — `Route` model

Plan strengths:
1. Well-scoped — route-level only, no code coverage or mutation testing
2. Reuses existing infrastructure (`parse_junit`, `enumerate_operations`, JUnit name extraction)
3. Clean CLI integration point under existing `analyze_app` group
4. Report `extras` pattern is well-established and extensible

Blocking issues:

1. **[P1] Plan must address overlap with existing `summarize_api_coverage()`** (`src/qaagent/report.py:802-848`)
   - `summarize_api_coverage()` already computes route-level coverage: it loads OpenAPI operations via `enumerate_operations()`, extracts covered operations from JUnit case names via `covered_operations_from_junit_case_names()`, and outputs `covered/total/pct/uncovered_samples`.
   - The proposed `route_coverage.py` module does essentially the same thing with better normalization and priority metadata.
   - Without addressing this, the implementation will either: (a) duplicate the logic, creating two parallel coverage computations, or (b) create confusing report output with both "API Coverage (Schemathesis)" and "Route Coverage Gaps" sections.
   - **Requested:** The plan should explicitly state the consolidation strategy. Options:
     - `route_coverage.py` replaces `summarize_api_coverage()` — the engine becomes the single source of truth, and `analyze_extras()` calls into it
     - `route_coverage.py` wraps/extends `summarize_api_coverage()` — keeps the existing function but adds normalization and priority on top
     - Document why both should coexist (different inputs/outputs/purposes)

2. **[P1] Open questions must be resolved before implementation**
   - "Should priority calculation consume `analyze risks` output directly in V1?" — This affects the module's interface and dependencies. If yes, `route_coverage.py` imports from `risk_assessment`. If no, priority is metadata-only (simpler, fewer coupling concerns).
   - "Should uncovered routes with deprecated tags be downgraded automatically?" — This affects the output schema and test fixtures.
   - **Requested:** Pick a concrete answer for each and update the plan. Recommendation: V1 should be metadata-only priority (no cross-command dependency) and defer deprecated-tag handling (keep it simple).

Non-blocking notes for implementation:
- The `Route` model (from `analyzers.models`) and `Operation` model (from `openapi_utils`) have different fields. The plan should clarify which model the gap engine normalizes to, or whether it defines its own canonical `(method, path)` representation.
- Test file location: `tests/integration/commands/test_analyze_cmd.py` is the better choice (matches existing test organization pattern).

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

Addressed both blocking issues in `docs/phases/phase9.md`.

Changes made:

1. **Consolidation strategy with existing `summarize_api_coverage()`**
   - Added explicit section: `P1.1 - Consolidation with Existing Report Coverage Logic`
   - Decision: new `route_coverage.py` engine is the single source of truth
   - `summarize_api_coverage()` remains as a compatibility wrapper delegating to the new engine and mapping to existing extras schema
   - Both report extras and new `analyze coverage-gaps` CLI will consume the same core engine to avoid duplicate implementations

2. **Open questions resolved**
   - Priority in V1 is metadata-only and deterministic (no direct dependency on `analyze risks`)
   - Deprecated-tag downgrades are deferred (not automatic in V1)
   - Replaced `Open Questions` with `Resolved Decisions` to remove ambiguity before implementation

3. **Non-blocking clarifications applied**
   - Added canonical representation details: internal coverage key is normalized `(METHOD, PATH)`
   - Updated integration test target to `tests/integration/commands/test_analyze_cmd.py`

Please re-review the updated plan for approval.

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Re-read the updated plan at `docs/phases/phase9.md` and verified all Round 1 feedback was addressed

Round 1 blockers resolved:

1. **Consolidation strategy** — New P1.1 section (lines 60-68) clearly states:
   - `route_coverage.py` is the single source of truth
   - `summarize_api_coverage()` retained as compatibility wrapper delegating to the new engine
   - Both report extras and CLI consume the same engine
   - Existing report output stays stable
   ✅

2. **Open questions resolved** — "Open Questions" replaced with "Resolved Decisions" (lines 120-122):
   - Priority: metadata-only and deterministic, no `analyze risks` dependency in V1
   - Deprecated-tag handling: deferred, no automatic downgrade
   ✅

Non-blocking clarifications also applied:
- Canonical `(METHOD, PATH)` representation documented in P1 (line 50)
- Integration test location corrected to `tests/integration/commands/test_analyze_cmd.py` (line 106)
- In-Scope updated to specify "route metadata only in V1" for prioritization (line 32)

Plan is clear, well-scoped, and internally consistent. No remaining concerns.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 2
STATE: approved
<!-- /CYCLE_STATUS -->
