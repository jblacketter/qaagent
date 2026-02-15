# Phase 13: Live DOM Inspection

## Status
- [x] Planning
- [x] Implementation
- [x] Complete

## Roles
- Lead: codex
- Reviewer: skipped (direct execution approved by user)

## Summary
**What:** Add `qaagent analyze dom` to inspect live pages with Playwright and produce selector/testability analysis.
**Why:** UI test quality depends on resilient selectors and form/navigation visibility that static route discovery cannot provide.
**Depends on:** Phase 12 (Notifications & Reporting) - Complete

## Scope

### In Scope
- Add Playwright-powered DOM analyzer module.
- Extract element inventory, selector coverage, forms, and navigation links.
- Generate selector strategy recommendations from DOM evidence.
- Add `qaagent analyze dom` command with profile-aware URL/auth defaults.
- Persist results to `dom-analysis.json`.
- Add unit and integration tests.
- Update CLI parity snapshot and project docs.

### Out of Scope
- Multi-page crawling and route graph expansion (`analyze routes --crawl`).
- LLM-driven DOM interpretation or autonomous UI exploration.
- Visual regression and screenshot diffing.

## Files Added
- `src/qaagent/analyzers/dom_analyzer.py`
- `tests/unit/analyzers/test_dom_analyzer.py`
- `docs/phases/phase13_impl.md`

## Files Modified
- `src/qaagent/commands/analyze_cmd.py`
- `tests/integration/commands/test_analyze_cmd.py`
- `tests/fixtures/cli_snapshots/pre_split_commands.json`
- `docs/ROADMAP.md`
- `docs/PROJECT_STATUS.md`

## Success Criteria
- [x] `qaagent analyze dom` command available and documented
- [x] DOM analysis JSON includes inventory, selectors, forms, and nav links
- [x] Auth/session defaults can be sourced from active profile settings
- [x] Selector strategy recommendations are generated from coverage gaps
- [x] Unit and integration tests cover analyzer + CLI behavior
