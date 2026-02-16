# Phase 9: Coverage Gap Analysis

## Status
- [x] Planning
- [x] In Review
- [ ] Approved
- [ ] Implementation
- [ ] Implementation Review
- [ ] Complete

## Roles
- Lead: codex
- Reviewer: claude
- Arbiter: Human

## Summary
**What:** Add route-level coverage gap analysis that maps discovered API operations against executed tests and reports uncovered/high-priority gaps.
**Why:** We already compute basic API coverage percentages, but we do not produce a concrete actionable list of uncovered operations tied to route inventory and risk context.
**Depends on:** Phase 8 (Parallel Test Execution) - Complete

## Context

Current coverage reporting (`qaagent report`) includes high-level summaries, and we already parse JUnit plus extract covered operations from test names. Phase 9 turns that into a first-class analysis surface with deterministic gap output and CLI/report integration.

## Scope

### In Scope
- Route-level coverage gap engine that:
  - loads route inventory from OpenAPI or `routes.json`
  - loads executed tests from JUnit artifacts and available test evidence
  - computes covered/uncovered operations with deterministic normalization
- Gap prioritization output (high/medium/low priority) using route metadata only in V1 (auth-required, tags, method/path characteristics)
- New CLI workflow for gap analysis (under `qaagent analyze`)
- Report integration so findings include route coverage gaps and top uncovered operations
- Unit + integration tests for mapper, CLI behavior, and report extras

### Out of Scope
- Branch/line code coverage instrumentation changes (`pytest-cov` behavior)
- Mutation testing or test quality scoring
- Dashboard UI redesign for coverage visualization
- Automatic test generation to close gaps (that is a follow-up phase)

## Technical Approach

### P1 - Coverage Mapping Engine

Create a dedicated analyzer to compute route coverage gaps from existing artifacts.

- New module: `src/qaagent/analyzers/route_coverage.py`
- Canonical internal key: `(METHOD, PATH)` where method is uppercased and path is normalized to templated form (for stable matching across sources)
- Inputs:
  - route inventory from OpenAPI operations and/or discovered routes
  - JUnit case names (reuse `parse_junit` + operation extraction patterns)
  - optional test evidence route fields when available
- Core behavior:
  - normalize route keys as `(METHOD, PATH)` in canonical form
  - compute aggregate totals and per-route status
  - emit stable sorted gap records for deterministic output/tests

### P1.1 - Consolidation with Existing Report Coverage Logic

`src/qaagent/report.py::summarize_api_coverage()` already performs a partial route-coverage computation. To avoid duplicate logic:

- `route_coverage.py` will become the single source of truth for route coverage calculations
- `summarize_api_coverage()` will be retained as a compatibility wrapper that delegates to `route_coverage.py` and maps to the current extras schema (`covered`, `total`, `pct`, `uncovered_samples`)
- `analyze_extras()` and new CLI coverage-gap output will both consume the same engine results

This keeps existing report output stable while removing parallel implementations.

### P2 - CLI Integration

Add `qaagent analyze coverage-gaps` in `src/qaagent/commands/analyze_cmd.py`.

Proposed command options:
- `--routes-file` (optional)
- `--openapi` (optional fallback)
- `--junit` (repeatable input)
- `--out` for JSON export
- `--markdown` optional narrative summary output

Behavior:
- uses active target/profile defaults when explicit inputs are absent
- prints summary table: total operations, covered, uncovered, coverage percent
- exits non-zero only for invalid/missing required inputs (not for uncovered gaps)

### P3 - Report Integration

Extend report extras to include route-level gap summary.

- Update `src/qaagent/report.py` to call the shared route coverage engine when OpenAPI + JUnit are available
- Include in markdown/html:
  - coverage percent
  - uncovered count
  - top uncovered operation samples
  - optional top-priority uncovered routes (new field in extras)

## Files to Create/Modify

### New Files
- `src/qaagent/analyzers/route_coverage.py` - route coverage/gap engine
- `tests/unit/analyzers/test_route_coverage.py` - unit tests for normalization, mapping, and prioritization

### Modified Files
- `src/qaagent/commands/analyze_cmd.py` - add `coverage-gaps` command
- `src/qaagent/report.py` - route coverage gap extras + rendering
- `tests/integration/commands/test_analyze_cmd.py` - CLI integration coverage
- `docs/PROJECT_STATUS.md` - mark Phase 9 progress when implementation starts

## Success Criteria
- [ ] Gap engine maps discovered operations to covered operations with deterministic output ordering
- [ ] Uncovered operations list includes method + path and priority metadata
- [ ] `qaagent analyze coverage-gaps` works with explicit files and active profile defaults
- [ ] JSON export includes totals, percent, and uncovered route records
- [ ] Report markdown/html include route coverage gap summary when inputs exist
- [ ] Existing report behavior remains unchanged when gap inputs are unavailable
- [ ] Unit tests cover normalization, matching, and edge cases (missing inputs, malformed JUnit)
- [ ] Integration tests validate CLI and report integration paths
- [ ] No regressions in existing analyze/report command behavior

## Resolved Decisions
- **Priority source (V1):** metadata-only and deterministic, with no direct dependency on `analyze risks` output.
- **Deprecated-tag handling (V1):** no automatic downgrade in this phase; defer to a future tuning phase to keep initial behavior explicit and testable.

## Risks
- **JUnit naming variability:** Some suites may not encode `METHOD PATH` in case names. Mitigation: combine JUnit extraction with route hints from test evidence where present and degrade gracefully.
- **Path normalization mismatches:** Route templates may differ (`/users/{id}` vs `/users/123`). Mitigation: canonical normalization plus explicit test fixtures for param patterns.
- **Input ambiguity:** Multiple route sources can conflict. Mitigation: deterministic precedence and explicit warnings in CLI output.
