# Phase 14: Live UI Route Crawling

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
**What:** Extend route discovery with live Playwright-based UI crawling via `qaagent analyze routes --crawl`.
**Why:** Static OpenAPI/source discovery misses runtime-only UI paths and navigation flows that matter for end-to-end test strategy.
**Depends on:** Phase 13 (Live DOM Inspection) - Complete

## Context

Current route discovery supports:
- OpenAPI parsing (`discover_from_openapi`)
- Source parsers (Python, Go, Ruby, Rust, Next.js source)
- Route aggregation and deduplication (`discover_routes`, `deduplicate_routes`)

Current gaps:
- No live UI crawl path in `discover_routes` (runtime crawl is placeholder only)
- No CLI option to discover routes by browser navigation
- No runtime route metadata model for crawl depth/page source confidence

## Scope

### In Scope
- Add a deterministic UI crawler that discovers routes from live navigation links.
- Add `analyze routes --crawl` workflow with crawl controls:
  - `--crawl`
  - `--crawl-url`
  - `--crawl-depth`
  - `--crawl-max-pages`
  - `--crawl-same-origin/--crawl-allow-external`
- Convert crawled pages into `Route` records (`GET`, `RouteSource.RUNTIME`) with crawl metadata.
- Merge crawled routes with OpenAPI/source-discovered routes through existing dedup pipeline.
- Reuse active profile defaults for crawl auth/session where possible (base URL, auth header token env, optional storage state).
- Add unit + integration tests and update CLI parity fixture if command shape changes.

### Out of Scope
- Multi-step interaction crawling (clicking arbitrary buttons, filling forms, modal flows).
- Auth flow automation/login scripting (assumes pre-auth headers/storage-state if needed).
- JavaScript event handler inference without URL transition.
- Visual regression, screenshot capture, or LLM-guided browser agents.

## Technical Approach

### P1 - Runtime Crawler Engine

Add `src/qaagent/analyzers/ui_crawler.py`:
- Headless Playwright crawl with BFS traversal.
- Seed URL queue from `crawl_url`.
- Extract candidate links from `a[href]` plus same-origin normalization.
- Track visited URLs and enforce hard limits (`max_pages`, `depth`).
- Normalize discovered paths:
  - remove query/fragment
  - collapse duplicate slashes
  - normalize trailing slash
- Return structured crawl records containing:
  - resolved URL
  - normalized path
  - depth
  - title (best-effort)
  - internal/external classification

Determinism guardrails:
- Stable BFS ordering
- Max links processed per page
- Hard timeout and explicit wait state handling

### P2 - Route Discovery Integration

Extend `src/qaagent/analyzers/route_discovery.py`:
- Add crawl options to `discover_routes(...)`.
- When crawl is enabled, call crawler and convert pages to `Route`:
  - `method="GET"`
  - `source=RouteSource.RUNTIME`
  - `confidence=0.6` (runtime-discovered from nav links)
  - metadata fields (`crawl_depth`, `crawl_url`, `title`, `internal`)
- Merge with OpenAPI/source routes using existing dedup strategy.

### P3 - CLI Wiring

Extend `src/qaagent/commands/analyze_cmd.py` (`analyze routes`):
- Add crawl flags/options.
- Resolve crawl start URL from precedence:
  1. `--crawl-url`
  2. `--target`
  3. active profile `app.dev.base_url`
- Reuse profile auth defaults similar to `analyze dom`:
  - auth header/token env
  - profile headers
  - optional storage-state path if present
- Surface crawl summary in CLI output:
  - pages visited
  - runtime routes discovered
  - merged total routes exported

### P4 - Tests and Documentation

Tests:
- `tests/unit/analyzers/test_ui_crawler.py`
  - URL normalization
  - same-origin filtering
  - depth/page limits
  - deterministic traversal behavior
- `tests/unit/analyzers/test_route_discovery.py`
  - runtime route conversion + dedup merge
- `tests/integration/test_analyze_routes_cli.py`
  - `--crawl` option behavior (mocked crawler)
  - active-profile crawl defaults

Docs:
- Phase implementation log (`docs/phases/phase14_impl.md`) during implementation
- Update roadmap/status after approval and implementation

## Files to Create/Modify

### New Files
- `src/qaagent/analyzers/ui_crawler.py`
- `tests/unit/analyzers/test_ui_crawler.py`
- `docs/phases/phase14_impl.md` (implementation phase)

### Modified Files
- `src/qaagent/analyzers/route_discovery.py`
- `src/qaagent/commands/analyze_cmd.py`
- `tests/unit/analyzers/test_route_discovery.py`
- `tests/integration/test_analyze_routes_cli.py`
- `tests/fixtures/cli_snapshots/pre_split_commands.json` (only if command tree changes)

## Success Criteria
- [x] `qaagent analyze routes --crawl` is available and documented via CLI help
- [x] Crawler discovers internal UI routes from live navigation links with bounded traversal
- [x] Runtime-discovered routes are exported as `RouteSource.RUNTIME` entries
- [x] Crawled + OpenAPI/source routes merge without duplicate regressions
- [x] Active profile defaults can seed crawl URL/auth/session settings
- [x] Unit/integration tests cover crawl engine and CLI integration paths
- [x] Existing `analyze routes` behavior remains backward compatible when `--crawl` is not used

## Open Questions
- Should query-string variants be collapsed to one canonical route in V1 (default proposed: yes)?
- Should crawl output include external links in route export or only internal links (default proposed: internal only)?

## Risks
- **Crawler flakiness on dynamic apps:** mitigate with deterministic settings, conservative waits, and strict limits.
- **Route noise from marketing/navigation pages:** mitigate with path normalization and optional include/exclude path filters in follow-up phase.
- **Auth-dependent route under-discovery:** mitigate by supporting headers/storage-state and explicit crawl URL overrides.
