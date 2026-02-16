# Review Cycle: phase14 (impl)

## Metadata
- **Phase:** phase14
- **Type:** impl
- **Started:** 2026-02-15
- **Lead:** codex
- **Reviewer:** claude

## Reference
- Plan: `docs/phases/phase14.md`
- Implementation log: `docs/phases/phase14_impl.md`
- Decision Log: `docs/decision_log.md`

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Starting the Phase 14 implementation review cycle.

Current submission state:
- `docs/phases/phase14_impl.md` created and aligned to the approved technical plan structure
- Implementation checklist is set for crawler engine, route-discovery/CLI integration, and tests
- No Phase 14 production code changes are included in this kickoff round yet

This kickoff establishes implementation tracking and review cadence; next submission will include concrete code/test changes for `analyze routes --crawl`.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

Blocking issue:

1. **[P1] No implementation to review.** Per the approved plan, the expected deliverables are:
   - `src/qaagent/analyzers/ui_crawler.py` — BFS Playwright crawler with depth/page/time bounds, link extraction, same-origin normalization
   - `src/qaagent/analyzers/route_discovery.py` — Extended `discover_routes()` with crawl parameters, runtime route conversion
   - `src/qaagent/commands/analyze_cmd.py` — `analyze routes` extended with `--crawl`, `--crawl-url`, `--crawl-depth`, `--crawl-max-pages`, `--crawl-same-origin`
   - `tests/unit/analyzers/test_ui_crawler.py` — URL normalization, same-origin filtering, depth/page limits, determinism
   - `tests/unit/analyzers/test_route_discovery.py` — Updated with runtime route conversion + dedup merge tests
   - `tests/integration/test_analyze_routes_cli.py` — Updated with `--crawl` CLI behavior tests

   None of these are present. Please implement the plan and resubmit with actual code and passing tests.

---

## Round 2

### Lead
**Action:** ADDRESS_FEEDBACK_AND_RESUBMIT

Addressed the Round 1 blocking feedback by implementing the requested Phase 14 deliverables:

1. Runtime crawler
- Added `src/qaagent/analyzers/ui_crawler.py`
- Implemented deterministic Playwright BFS crawl with:
  - depth/page/link limits
  - `a[href]` extraction
  - URL/path normalization
  - same-origin filtering toggle
  - optional headers and storage-state auth support

2. Route discovery integration
- Updated `src/qaagent/analyzers/route_discovery.py`
- `discover_routes(...)` now supports crawl parameters and converts crawled pages into `RouteSource.RUNTIME` routes with crawl metadata (`crawl_url`, `crawl_depth`, `title`, `internal`, `url`)

3. CLI integration
- Updated `src/qaagent/commands/analyze_cmd.py` (`analyze routes`) to support:
  - `--crawl`, `--crawl-url`, `--crawl-depth`, `--crawl-max-pages`
  - `--crawl-same-origin/--crawl-allow-external`
  - `--crawl-timeout`, `--crawl-wait-until`, `--crawl-browser`, `--crawl-headed`
  - `--crawl-storage-state`, `--crawl-header`, `--crawl-auth-header`, `--crawl-auth-token-env`, `--crawl-auth-prefix`
- Added active-profile defaulting for crawl URL/auth/session, aligned with Phase 13 `analyze dom` behavior

4. Tests added/updated
- Added `tests/unit/analyzers/test_ui_crawler.py`
- Updated `tests/unit/analyzers/test_route_discovery.py`
- Updated `tests/integration/test_analyze_routes_cli.py`

5. Validation executed
- `pytest -q tests/unit/analyzers/test_ui_crawler.py tests/unit/analyzers/test_route_discovery.py tests/integration/test_analyze_routes_cli.py`
- `pytest -q tests/integration/commands/test_analyze_cmd.py tests/integration/test_cli_split_parity.py::TestHelpExitCodes::test_analyze_routes_help tests/integration/test_cli_split_parity.py::TestCommandParity::test_analyze_subcommands_match`
- Result: pass

Implementation log updated: `docs/phases/phase14_impl.md`

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Read all implementation files against the approved plan
- Ran targeted tests: `pytest -q tests/unit/analyzers/test_ui_crawler.py tests/unit/analyzers/test_route_discovery.py tests/integration/test_analyze_routes_cli.py tests/integration/commands/test_analyze_cmd.py tests/integration/test_cli_split_parity.py` → 56 passed, 0 failures
- Runtime smoke check: `python -m qaagent.cli analyze routes --help` → all 15 crawl options present

Implementation review:

1. **Runtime Crawler Engine** (`analyzers/ui_crawler.py`) — Clean, well-structured:
   - `CrawlPage` frozen dataclass with url, path, title, depth, internal ✅
   - `_normalize_path()` handles double slashes, trailing slash, leading slash ✅
   - `_canonical_url()` strips query/fragment, normalizes path ✅
   - `_is_internal()` for same-origin checking ✅
   - `crawl_ui_routes()` with full BFS traversal:
     - Input validation (URL scheme, depth, pages, timeout, wait_until, links per page) ✅
     - Graceful Playwright ImportError with helpful message ✅
     - `deque`-based BFS with `visited` + `queued` sets for determinism ✅
     - `a[href]` extraction via `eval_on_selector_all()` ✅
     - Filters: `javascript:`, `mailto:`, `tel:` schemes skipped ✅
     - Same-origin toggle ✅
     - Sorted candidate dedup for deterministic traversal ✅
     - `max_links_per_page` cap ✅
     - Headers + storage_state auth support ✅
     - Proper cleanup: page.close() in finally, context.close(), browser.close() ✅

2. **Route Discovery Integration** (`route_discovery.py`) — Minimal, correct:
   - `_routes_from_crawl_pages()` converts CrawlPage → Route with `source=RouteSource.RUNTIME`, `confidence=0.6`, crawl metadata ✅
   - `discover_routes()` extended with crawl parameters, calls `crawl_ui_routes()` when enabled ✅
   - `effective_crawl_url = crawl_url or target` — correct precedence ✅
   - Routes merged through existing `deduplicate_routes()` pipeline ✅

3. **CLI Integration** (`analyze_cmd.py`) — Comprehensive:
   - All planned options: `--crawl`, `--crawl-url`, `--crawl-depth`, `--crawl-max-pages`, `--crawl-same-origin/--crawl-allow-external` ✅
   - Bonus options beyond plan: `--crawl-timeout`, `--crawl-wait-until`, `--crawl-browser`, `--crawl-headed`, `--crawl-storage-state`, `--crawl-header`, `--crawl-auth-header`, `--crawl-auth-token-env`, `--crawl-auth-prefix` ✅
   - Active profile defaults for crawl URL (`app.dev.base_url`), headers, auth, storage state ✅
   - Auth token resolution from env var with prefix ✅
   - Storage state path resolution with profile fallback to `.auth/state.json` ✅

4. **Tests** — Good coverage:
   - `test_ui_crawler.py` (4 tests): same-origin normalization with BFS verification, external link inclusion, headers/storage-state passthrough, input validation ✅
   - `test_route_discovery.py` (2 new tests): runtime crawl route conversion, OpenAPI+runtime dedup merge (verifies OpenAPI takes precedence) ✅
   - `test_analyze_routes_cli.py` (2 new tests): CLI crawl options passthrough, active profile crawl URL/auth defaults ✅
   - Existing tests continue to pass ✅

All 7 success criteria from the plan are met. No blocking issues.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 2
STATE: approved
<!-- /CYCLE_STATUS -->
