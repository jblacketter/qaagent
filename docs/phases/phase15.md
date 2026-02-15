# Phase 15: AI-Assisted Test Recording

## Status
- [x] Planning
- [x] In Review
- [x] Approved
- [x] Implementation
- [x] Implementation Review
- [x] Complete

## Roles
- Lead: codex
- Reviewer: claude
- Arbiter: Human

## Summary
**What:** Add `qaagent record` to capture browser user flows and export them as Playwright and Behave test assets.
**Why:** Route/discovery analysis is now strong, but users still need a fast path to turn real exploratory flows into executable regression tests.
**Depends on:** Phase 14 (Live UI Route Crawling) - Complete

## Context

The codebase now has:
- Live DOM inspection (`analyze dom`)
- Runtime UI route discovery (`analyze routes --crawl`)
- Generators for Playwright and Behave test suites

Missing capability:
- A first-party flow recorder that captures real browser interactions and converts them into reusable test code.

## Scope

### In Scope
- Add a new command: `qaagent record`.
- Capture key browser actions from an active page session:
  - navigation
  - click
  - fill/type
  - select/check/uncheck
  - submit
- Persist normalized action timeline as JSON (`recording.json`).
- Export captured flow to:
  - Playwright TypeScript spec
  - Behave `.feature` + step skeleton
- Provide deterministic selector strategy fallback order:
  - `data-testid`
  - ARIA/role-label
  - id/name
  - scoped CSS fallback (last resort)
- Add tests for normalization, selector generation, exporter output, and CLI behavior.

### Out of Scope
- Fully autonomous agent navigation and goal planning.
- Multi-tab/session orchestration.
- Video/screenshot post-processing and visual diff.
- Cloud storage or hosted recording replay services.

## Technical Approach

### P1 - Recording Core

Add recording package under `src/qaagent/recording/`:
- `models.py`
  - `RecordedAction`, `RecordedFlow`, `SelectorCandidate`
- `recorder.py`
  - Playwright-driven recording session
  - bounded action capture (`max_actions`, `timeout_seconds`)
  - normalized event stream + dedup/coalescing (e.g., typing bursts)
- `selectors.py`
  - deterministic selector extraction and ranking policy
  - fallback handling when stable selectors are absent

Output artifact:
- `.qaagent/recordings/<timestamp>/recording.json`

Event capture mechanism (V1):
- Inject DOM listeners with `page.add_init_script(...)` / `page.evaluate(...)` to capture `click`, `input`, `change`, and `submit` events into an in-page queue.
- Poll and drain that queue from Python on a short interval (`page.evaluate(...)`) so action ordering is deterministic.
- Capture navigation actions via Playwright `page.on("framenavigated")` and normalize to URL transitions.
- Keep V1 browser-agnostic (avoid CDP-only dependencies) so chromium/firefox/webkit remain supported.

### P2 - Exporters

Add export module(s):
- `export_playwright.py`
  - render Playwright spec from normalized actions
  - include waits/assertable checkpoints for key navigations
- `export_behave.py`
  - render Gherkin scenario + step definition stubs

Export targets:
- `tests/qaagent/e2e/recorded_<name>.spec.ts`
- `tests/qaagent/behave/features/recorded_<name>.feature`

### P3 - CLI Integration

Add command module:
- `src/qaagent/commands/record_cmd.py`

CLI shape (proposed V1):
- `qaagent record --url <start_url> --name <flow_name>`
- options:
  - `--browser`
  - `--headed/--headless`
  - `--timeout`
  - `--max-actions`
  - `--out-dir`
  - `--storage-state`
  - `--header` (repeatable)
  - `--export playwright|behave|both`

Profile-aware defaults:
- resolve URL/auth/session from active profile when omitted

### P4 - Validation and Safety

- Add explicit redaction for sensitive typed values in stored recording:
  - passwords
  - token-like fields
- Add JSON schema-level validation for persisted recording payload.
- Ensure deterministic exporter output for stable tests/diffs.

### P5 - Tests

Unit:
- `tests/unit/recording/test_selectors.py`
- `tests/unit/recording/test_recorder.py`
- `tests/unit/recording/test_export_playwright.py`
- `tests/unit/recording/test_export_behave.py`

Integration:
- `tests/integration/commands/test_record_cmd.py`
- CLI parity snapshot update if command tree changes.

## Files to Create/Modify

### New Files
- `src/qaagent/recording/__init__.py`
- `src/qaagent/recording/models.py`
- `src/qaagent/recording/recorder.py`
- `src/qaagent/recording/selectors.py`
- `src/qaagent/recording/export_playwright.py`
- `src/qaagent/recording/export_behave.py`
- `src/qaagent/commands/record_cmd.py`
- `tests/unit/recording/test_selectors.py`
- `tests/unit/recording/test_recorder.py`
- `tests/unit/recording/test_export_playwright.py`
- `tests/unit/recording/test_export_behave.py`
- `tests/integration/commands/test_record_cmd.py`
- `docs/phases/phase15_impl.md` (implementation phase)

### Modified Files
- `src/qaagent/commands/__init__.py` (register `record` command)
- `tests/fixtures/cli_snapshots/pre_split_commands.json` (if command tree changes)
- `docs/ROADMAP.md` and `docs/PROJECT_STATUS.md` (post-implementation status updates)

## Success Criteria
- [x] `qaagent record` command is available with clear CLI help/options
- [x] Recording session persists normalized `recording.json` action timeline
- [x] Export to Playwright spec works from recorded timeline
- [x] Export to Behave feature/steps works from recorded timeline
- [x] Selector strategy prefers stable selectors and only falls back to CSS when needed
- [x] Sensitive input redaction is applied in persisted recordings
- [x] Unit + integration tests cover core recording/export flows
- [x] Existing CLI command behavior remains backward compatible

## Resolved Decisions
- **Stop condition (V1):** dual bounded capture using `max_actions` and `timeout_seconds`; recording stops when either threshold is reached. Keyboard shortcuts/prompts are deferred.
- **Assertions in exports (V1):** include URL assertions after navigation actions by default (deterministic and low-noise). Additional assertion types remain optional follow-up work.
- **Capture backend (V1):** injected DOM listeners + periodic queue drain + `framenavigated` hooks for navigation events (cross-browser, dependency-light).

## Risks
- **Noisy event streams:** mitigated by normalization/coalescing rules and max action caps.
- **Flaky selectors:** mitigated by stable-selector ranking and explicit fallback policy.
- **Sensitive data leakage:** mitigated with redaction heuristics and masked persistence.
