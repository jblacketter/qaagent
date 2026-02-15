# Review Cycle: phase14 (plan)

## Metadata
- **Phase:** phase14
- **Type:** plan
- **Started:** 2026-02-15
- **Lead:** codex
- **Reviewer:** claude

## Reference
- Plan: `docs/phases/phase14.md`
- Implementation: N/A (plan review)

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 14 plan: **Live UI Route Crawling**.

Plan highlights:
- Add a new runtime crawler (`ui_crawler.py`) using deterministic Playwright BFS traversal with depth/page/time bounds.
- Extend `discover_routes(...)` so `--crawl` discoveries are emitted as `RouteSource.RUNTIME` and merged with OpenAPI/source routes.
- Add `qaagent analyze routes --crawl` options for runtime navigation discovery (`--crawl-url`, depth/max-pages, same-origin behavior).
- Reuse active-profile defaults for crawl base URL and auth/session setup where possible.
- Add targeted unit/integration tests for crawler normalization, merge semantics, and CLI behavior.

Planned scope is intentionally limited to link-based route discovery in V1. It excludes multi-step interaction crawling and agentic browser actions.

### Reviewer
**Action:** APPROVE

Verdict: APPROVE

What I validated:
- Read the full plan at `docs/phases/phase14.md`
- Cross-referenced against existing source files: `analyzers/models.py` (RouteSource.RUNTIME already defined), `analyzers/route_discovery.py` (placeholder at line 253, deduplicate_routes with confidence-based merging), `commands/analyze_cmd.py` (existing `analyze routes` options, `analyze dom` auth/session pattern from Phase 13), existing tests
- Verified Phase 13 dependency is COMPLETE (Playwright infrastructure proven)

Plan review:

1. **Runtime Crawler Engine (P1)** — Well-designed:
   - BFS traversal with depth/page/time bounds is the right approach for V1
   - Link extraction from `a[href]` with same-origin normalization is appropriate scope
   - Determinism guardrails (stable BFS, max links per page, hard timeout) are essential
   - Path normalization (query/fragment removal, collapse slashes, trailing slash) aligns with existing `normalize_path()` patterns
   ✅

2. **Route Discovery Integration (P2)** — Clean hook point:
   - Existing placeholder at `discover_routes()` line 253 (`if target: pass`) ready for integration
   - `RouteSource.RUNTIME` already defined in models
   - Confidence=0.6 ensures OpenAPI (1.0) and source (0.9) routes take precedence in dedup
   - Metadata fields (crawl_depth, crawl_url, title, internal) provide good provenance
   ✅

3. **CLI Wiring (P3)** — Practical:
   - `--crawl` flag plus `--crawl-url`, `--crawl-depth`, `--crawl-max-pages`, `--crawl-same-origin` are clear
   - URL precedence (explicit > target > profile) is well-defined
   - Auth/session reuse from Phase 13 `analyze dom` pattern is sensible
   - Crawl summary in CLI output (pages visited, routes discovered, merged total) is useful
   ✅

4. **Tests (P4)** — Comprehensive coverage plan:
   - Unit tests for crawler normalization, same-origin filtering, depth/page limits, determinism
   - Unit tests for runtime route conversion + dedup merge
   - Integration tests for CLI `--crawl` behavior with mocked crawler
   ✅

5. **Success Criteria** — All 7 criteria are testable and well-defined ✅

6. **Scope Boundaries** — Explicitly excludes multi-step interaction, form filling, auth automation, visual regression. Good for V1. ✅

Advisory notes (non-blocking):

1. **Open questions should be resolved**: The plan lists 2 open questions with "default proposed" answers. I agree with both defaults (collapse query strings: yes; export internal only: yes). These should be marked as resolved decisions before implementation.

2. **Crawl timeout CLI option**: The plan mentions "hard timeout" in guardrails but doesn't expose it as a CLI option (e.g., `--crawl-timeout`). Consider adding one for CI/pipeline use, or at minimum define the default in the plan.

3. **Playwright graceful degradation**: The crawler requires Playwright (optional dependency). Phase 13 likely established the pattern for graceful ImportError handling. Ensure the crawler follows the same pattern.

All three notes are implementation details. The architecture is sound, scope is well-bounded, and all foundational pieces (RouteSource, dedup, Playwright infra, auth pattern) are already in place.

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: none
ROUND: 1
STATE: approved
<!-- /CYCLE_STATUS -->
