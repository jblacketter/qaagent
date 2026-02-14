# Review Cycle: phase6 (impl)

## Metadata
- **Phase:** phase6
- **Type:** impl
- **Started:** 2026-02-13
- **Lead:** claude
- **Reviewer:** codex

## Reference
- Plan: `docs/phases/phase6.md` (plan file at `~/.claude/plans/stateful-bouncing-pixel.md`)
- Implementation: See files list below
- Decision Log: `docs/decision_log.md`

---

## Round 1

### Lead
**Action:** SUBMIT_FOR_REVIEW

Implementation of Phase 6 "App Documentation & Architecture Mapping" is complete across all 6 priorities (P1-P6). 81 files changed, ~7,100 lines added, 925 tests passing.

**Files Created (new modules):**

P1 — Core Documentation Engine (9 files):
- `src/qaagent/doc/__init__.py` — Package init, exports public API
- `src/qaagent/doc/models.py` — Pydantic models: IntegrationType, RouteDoc, FeatureArea, Integration, DiscoveredCUJ, ArchitectureNode/Edge, AppDocumentation
- `src/qaagent/doc/feature_grouper.py` — Groups routes into FeatureAreas by tag (primary) or path prefix (fallback), detects CRUD ops
- `src/qaagent/doc/integration_detector.py` — AST-based detection of external services from Python imports, env vars, JS package.json
- `src/qaagent/doc/generator.py` — Orchestrator: discover_routes → group → detect integrations → apply config → link → hash → CUJs → graphs → prose
- `src/qaagent/doc/prose.py` — LLM prose synthesis with template fallback
- `src/qaagent/doc/cuj_discoverer.py` — CUJ auto-discovery with 5 pattern detectors (auth, CRUD, checkout, onboarding, search)
- `src/qaagent/doc/graph_builder.py` — Builds 3 architecture diagram types (feature map, integration map, route graph)
- `src/qaagent/doc/markdown_export.py` — Renders AppDocumentation to structured markdown

P2 — CLI Commands (1 file):
- `src/qaagent/commands/doc_cmd.py` — Typer subapp: `doc generate`, `doc show`, `doc export`, `doc cujs`

P3 — API Routes & Dashboard (14 files):
- `src/qaagent/api/routes/doc.py` — FastAPI router: GET/POST endpoints for doc, features, integrations, CUJs, architecture, regenerate, export
- `src/qaagent/dashboard/frontend/src/pages/AppDoc.tsx` — Main doc page with summary, feature grid, integration cards, CUJ list
- `src/qaagent/dashboard/frontend/src/pages/FeatureDetail.tsx` — Feature deep-dive with route table and connected integrations
- `src/qaagent/dashboard/frontend/src/pages/Integrations.tsx` — Integration list with type filtering
- `src/qaagent/dashboard/frontend/src/pages/Architecture.tsx` — Architecture page with tab selector for 3 diagram types
- `src/qaagent/dashboard/frontend/src/components/Doc/FeatureCard.tsx` — Feature area card component
- `src/qaagent/dashboard/frontend/src/components/Doc/IntegrationCard.tsx` — Integration card component
- `src/qaagent/dashboard/frontend/src/components/Doc/RouteTable.tsx` — Route table component
- `src/qaagent/dashboard/frontend/src/components/Doc/CujCard.tsx` — Expandable CUJ card component
- `src/qaagent/dashboard/frontend/src/components/Doc/StalenessBar.tsx` — Freshness indicator (green/yellow/red) with regenerate button
- `src/qaagent/dashboard/frontend/src/components/Doc/FeatureMapDiagram.tsx` — React Flow feature map
- `src/qaagent/dashboard/frontend/src/components/Doc/IntegrationMapDiagram.tsx` — React Flow integration map
- `src/qaagent/dashboard/frontend/src/components/Doc/RouteGraphDiagram.tsx` — React Flow route graph
- `src/qaagent/dashboard/frontend/src/components/Doc/nodes/FeatureNode.tsx` — Custom React Flow node
- `src/qaagent/dashboard/frontend/src/components/Doc/nodes/IntegrationNode.tsx` — Custom React Flow node
- `src/qaagent/dashboard/frontend/src/components/Doc/nodes/RouteGroupNode.tsx` — Custom React Flow node

Tests (8 files, ~160 tests):
- `tests/unit/doc/test_models.py` — 21 tests: model serialization/roundtrip
- `tests/unit/doc/test_feature_grouper.py` — 22 tests: grouping logic
- `tests/unit/doc/test_integration_detector.py` — 26 tests: detection
- `tests/unit/doc/test_generator.py` — 17 tests: generator orchestrator
- `tests/unit/doc/test_markdown_export.py` — 10 tests: markdown rendering
- `tests/unit/doc/test_graph_builder.py` — 14 tests: graph builder
- `tests/unit/doc/test_cuj_discoverer.py` — 17 tests: CUJ discovery
- `tests/unit/doc/test_config_overrides.py` — 13 tests: config override merging
- `tests/unit/api/routes/test_doc.py` — 10 tests: API route tests
- `tests/integration/commands/test_doc_cmd.py` — 10 tests: CLI integration tests

**Files Modified:**
- `src/qaagent/commands/__init__.py` — Added `doc_app` registration
- `src/qaagent/config/models.py` — Added `DocIntegrationOverride`, `DocSettings`, and `doc` field on `QAAgentProfile`
- `src/qaagent/api/app.py` — Added doc router registration
- `src/qaagent/dashboard/frontend/package.json` — Added `@xyflow/react` dependency
- `src/qaagent/dashboard/frontend/src/App.tsx` — Added `/doc/*` routes
- `src/qaagent/dashboard/frontend/src/components/Layout/Sidebar.tsx` — Added App Docs nav link
- `src/qaagent/dashboard/frontend/src/services/api.ts` — Added doc API methods
- `src/qaagent/dashboard/frontend/src/types/index.ts` — Added TypeScript interfaces
- `tests/fixtures/cli_snapshots/pre_split_commands.json` — Added `doc` subcommand
- `tests/integration/test_cli_split_parity.py` — Added doc subcommand parity tests

**Test results:** 925 tests pass (excluding 3 pre-existing failures: `test_full_api_workflow`, `test_mcp_server_initializes`, `test_deduplicate_routes_prefers_higher_confidence`).

**Key implementation decisions:**
- Storage: `appdoc.json` in `.qaagent/` directory (version-controllable, project-scoped)
- LLM role: prose synthesis only; all structural extraction is deterministic with template fallback
- Content hash + timestamp for staleness detection
- Lazy import patching: must patch at source module, not consumer module
- Custom summary override applied AFTER prose synthesis so it takes precedence

**Review focus areas:**
1. Feature grouper: handling of mixed tagged/untagged routes with same prefix
2. Integration detector: directory exclusion patterns (virtualenvs, vendor dirs)
3. API regeneration endpoint: whether it correctly passes all config overrides
4. `doc cujs --merge` command: currently only previews, doesn't persist

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- All planned P1-P6 files exist and tests pass: `pytest tests/unit/doc tests/unit/api/routes/test_doc.py tests/integration/commands/test_doc_cmd.py` — 160 passed.
- CLI snapshot parity test passes with `doc` subcommand.
- Architecture is sound: deterministic extraction + optional LLM prose is the right pattern.

Blocking issues:

1. **[P1] API regeneration ignores profile doc settings** (`src/qaagent/api/routes/doc.py:109-113`): The regeneration endpoint loads the active profile but only passes `source_dir`, `app_name`, and `use_llm` into `generate_documentation`; it omits `openapi_path` and `doc_settings`. Dashboard regeneration produces different output than `qaagent doc generate` (loses custom summaries, exclusions, manual integrations, and routes from configured OpenAPI specs).

2. **[P2] CLI `doc generate` ignores configured OpenAPI spec** (`src/qaagent/commands/doc_cmd.py:37-43`): `doc_generate` loads the active profile but only sets `openapi_path` from the `--openapi` flag. A configured `openapi.spec_path` is ignored unless the user re-types it on every run, producing incomplete/empty docs for repos that depend on the configured spec.

3. **[P2] Feature grouper produces duplicate feature IDs** (`src/qaagent/doc/feature_grouper.py:91-98`): Tagged routes and untagged-prefix routes are appended as separate `FeatureArea` objects. Mixed datasets produce duplicate feature IDs (e.g., tagged `/users` + untagged `/users/{id}` → two `id="users"` entries). Breaks `/doc/features/{feature_id}` (returns first match only) and graph node IDs.

4. **[P2] `doc cujs --merge` doesn't persist** (`src/qaagent/commands/doc_cmd.py:232-236`): The `--merge` option computes `new_journeys` and prints "Would add..." but never writes to `cuj.yaml`. Users expect persistent changes but nothing is merged.

Non-blocking observations:
- Integration detector scans virtualenv/site-packages directories, which can produce false positives and slow scans on large repos. Consider skipping `.venv`, `venv`, `site-packages`, `__pycache__` directories.
- `from rich import print` in `doc_cmd.py` shadows the builtin `print` — not a bug but potentially confusing.

Please fix the 4 blocking issues and resubmit for review.

---

## Round 2

### Lead
**Action:** SUBMIT_FOR_REVIEW

All 4 blocking issues from Round 1 are resolved, plus the non-blocking virtualenv scanning issue.

**1. [P1] API regeneration now passes `doc_settings` and `openapi_path`** (`src/qaagent/api/routes/doc.py:95-126`)
- `regenerate_doc()` now extracts `doc_settings = profile.doc` and `openapi_path = profile.resolve_spec_path(project_root)` from the active profile
- Both are passed to `generate_documentation()`, so dashboard regeneration produces identical output to `qaagent doc generate`
- 2 new tests: `test_regenerate_passes_doc_settings` (verifies custom_summary flows through) and `test_regenerate_passes_openapi_path`

**2. [P2] CLI `doc generate` now uses configured OpenAPI spec** (`src/qaagent/commands/doc_cmd.py:26-38`)
- When `--openapi` flag is not provided, falls back to `active_profile.resolve_spec_path(project_root)`
- Explicit `--openapi` flag still takes precedence

**3. [P2] Feature grouper merges duplicate feature IDs** (`src/qaagent/doc/feature_grouper.py:88-107`)
- Tagged and untagged route groups are merged by slug before building `FeatureArea` objects
- Mixed datasets (tagged `/users` + untagged `/users/{id}`) now produce a single feature with all routes
- 2 new tests: `test_merges_tagged_and_untagged_with_same_slug` and `test_no_duplicate_feature_ids`

**4. [P2] `doc cujs --merge` now persists to `cuj.yaml`** (`src/qaagent/commands/doc_cmd.py:226-256`)
- Reads existing YAML data, appends new journeys, writes back to `handoff/cuj.yaml`
- Creates `handoff/` directory if it doesn't exist
- Output message changed from "Would add" to "Added"

**Non-blocking: Integration detector now skips virtualenvs** (`src/qaagent/doc/integration_detector.py:128-135`)
- Added `skip_dirs` set: `.venv`, `venv`, `site-packages`, `__pycache__`, `.git`, `.tox`, `.mypy_cache`
- Applied to both Python and JS/TS file scanning
- 2 new tests: `test_skips_virtualenv` and `test_skips_pycache`

**Test results:** 931 tests pass (166 doc-specific, 6 new tests added this round). 0 regressions.

### Reviewer
_awaiting response_

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: reviewer
ROUND: 2
STATE: in-progress
<!-- /CYCLE_STATUS -->
