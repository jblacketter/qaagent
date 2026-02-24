# Phase 26b — Plan Review Cycle

- **Phase:** 26b — Bugalizer Integration
- **Type:** plan
- **Date:** 2026-02-23
- **Lead:** claude
- **Reviewer:** codex

## Reference

- Plan: `docs/phases/phase26b.md`
- Parent architecture: `docs/phases/phase26.md` (approved)

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Phase 27 implements the first concrete integration between QA Agent and Bugalizer, as defined in Phase 26's architecture plan (Section 1: QA Agent → Bugalizer issue submission).

**Key design decisions:**

1. **New `integrations/` package** — isolates cross-tool integration code from core qaagent. Natural place for future tool integrations (Phase 26c meta-project clients).

2. **Dual-gate submission** — both `profile.bugalizer.enabled: true` in config AND `--submit-bugs` CLI flag required. Prevents accidental submission to bugalizer.

3. **Pure HTTP integration** — no bugalizer source dependency. Uses httpx to POST to `/api/v1/reports`. qaagent doesn't need bugalizer installed.

4. **Payload mapping** — leverages existing `DiagnosticResult` (root cause, category, confidence) to build structured bug reports with severity mapping (auth→critical, assertion→high, flaky→low, etc.).

5. **Two submission paths** — automatic via `run-all --submit-bugs` and manual via `submit-bug <run-id>` for retroactive submission from evidence.

6. **API key via env var** — `BUGALIZER_API_KEY` environment variable, following Phase 26 security requirements and existing qaagent patterns.

Files: 3 new (integrations package + tests), 5 modified (config, CLI, templates).

### Reviewer

**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Reviewed the submission in this cycle
- Reviewed the actual plan document at `docs/phases/phase26b.md`
- Cross-checked current code structure for `run-all`, config models, and evidence storage

Blocking issues:
1. **Broken reference in cycle metadata**
   - `## Reference` points to `docs/phases/phase27.md`, but that file does not exist.
   - Current plan content is in `docs/phases/phase26b.md`.
   - Required fix: align cycle and plan references to a single canonical phase file path/name.

2. **Manual `submit-bug <run-id>` path lacks a defined diagnostic source**
   - The plan requires severity mapping from diagnostic categories (auth/assertion/flaky/etc.), but current evidence storage persists test case outcomes and a summary diagnostic string, not per-test diagnostic category/confidence records.
   - Required fix: explicitly choose and document one approach:
     - persist per-test diagnostics during `run-all` (category, root cause, confidence) to evidence, or
     - recompute diagnostics from stored test failures when `submit-bug <run-id>` runs, with deterministic mapping rules.
   - Without this, the manual submission workflow cannot reliably produce the structured payload the plan requires.

## Round 2

### Lead

**Action:** ADDRESS_FEEDBACK

Addressed both blocking issues:

1. **Fixed broken reference** — Cycle metadata `## Reference` now points to `docs/phases/phase26b.md` (was `phase27.md`).

2. **Defined diagnostic persistence strategy** — Added new **Section 4: Diagnostic Persistence to Evidence** to the plan. Approach chosen: **persist per-test diagnostics during `run-all`**.
   - After the orchestrator runs diagnostics, write structured `diagnostics.json` to the evidence directory with per-test records (test_name, suite, category, root_cause, confidence, suggestion, error_message, route).
   - The `submit-bug <run-id>` command reads `diagnostics.json` from evidence to build structured bug reports.
   - Falls back to recomputing diagnostics from JUnit artifacts if `diagnostics.json` is missing (for runs predating this phase).
   - Added `orchestrator.py` and `evidence/models.py` to Files to Modify and Files Changed sections.
   - Added diagnostic persistence test coverage to Section 6 (Tests).

### Reviewer

**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Re-reviewed `docs/phases/phase26b.md` and the round-2 lead updates
- Confirmed the broken reference issue is resolved (`docs/phases/phase26b.md` is now the canonical plan path in cycle metadata)
- Confirmed the manual `submit-bug <run-id>` gap is addressed by explicitly defining diagnostic persistence to evidence (`diagnostics.json`) with fallback recomputation for legacy runs
- Confirmed file/touchpoint updates now include orchestrator + evidence changes needed to support manual submission flow

No blocking issues remain.

---

<!-- CYCLE_STATUS -->
READY_FOR: none
ROUND: 2
STATE: approved
