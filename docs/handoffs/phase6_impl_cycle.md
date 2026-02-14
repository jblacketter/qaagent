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
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Round 1 fixes confirmed: API regeneration passes doc_settings/openapi, CLI uses configured spec, feature grouper merges duplicates, --merge persists.
- All 166 tests pass.

Blocking issues:

1. **[P2] False auth flow detection from "auth" keyword** (`src/qaagent/doc/cuj_discoverer.py:67`): Using "auth" as a login keyword causes false positives — a codebase with only `POST /auth/register` (no login route) still detects an auth flow using register as the login step.

2. **[P2] Unreadable Python files crash integration scanning** (`src/qaagent/doc/integration_detector.py:154-157`): `_scan_python_file` catches parse errors but not filesystem read errors (PermissionError), so a single unreadable `.py` file aborts doc generation entirely.

3. **[P3] Wildcard route-prefix counting inflates stats** (`src/qaagent/doc/graph_builder.py:210-212`): Path params like `{id}` match any static prefix segment, so `/users/{id}` gets counted under `/users/orders`. This inflates route_count in route-graph nodes.

---

## Round 3

### Lead
**Action:** SUBMIT_FOR_REVIEW

All 3 blocking issues from Round 2 are resolved.

**1. [P2] Removed "auth" from login keywords** (`src/qaagent/doc/cuj_discoverer.py:67`)
- Removed generic "auth" keyword from login route matching
- Login detection now requires specific keywords: "login", "signin", "authenticate"
- 1 new test: `test_no_false_positive_from_auth_prefix_only`

**2. [P2] Handle filesystem errors in integration scanning** (`src/qaagent/doc/integration_detector.py:157`)
- Added `OSError` to the except clause in `_scan_python_file`
- Unreadable files are silently skipped, matching JS scanner behavior

**3. [P3] Fixed wildcard route-prefix counting** (`src/qaagent/doc/graph_builder.py:200-215`)
- Path param segments are filtered out before prefix comparison
- `/users/{id}/profile` no longer falsely matches prefix `/users/orders`
- 4 new tests in `TestPathMatchesPrefix` class

**Test results:** 936 tests pass (171 doc-specific). 0 regressions.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Round 2 fixes confirmed: versioned prefix edges fixed, duplicate override IDs fixed.
- All 173 doc tests pass.

Blocking issues:

1. **[P1] Missing OpenAPI file crashes doc generation** (`src/qaagent/doc/generator.py:139-141`): When profile points to a stale/missing spec file, `discover_from_openapi()` raises `FileNotFoundError`. Both CLI and API generation fail before source-based discovery can run.

2. **[P2] Auto-detected integrations have no feature connections** (`src/qaagent/doc/generator.py:50-55`): `IntegrationDetector` emits integrations with empty `connected_features`, and `_link_integrations_to_features()` only validates pre-existing values. Architecture diagrams show no integration edges unless users provide manual overrides.

---

## Round 4

### Lead
**Action:** SUBMIT_FOR_REVIEW

Both blocking issues from Round 3 are resolved.

**1. [P1] Gracefully skip nonexistent OpenAPI files** (`src/qaagent/doc/generator.py:138-143`)
- Added existence check before passing `openapi_path` to `discover_routes()`
- Missing spec files are silently skipped; source-based discovery still runs
- 1 new test: `test_regenerate_skips_missing_openapi`

**2. [P2] Auto-link integrations to all features** (`src/qaagent/doc/generator.py:48-56`)
- When `connected_features` is empty, assign all feature IDs (sorted for determinism)
- Architecture diagrams now show integration edges for auto-detected services
- Updated existing test for openapi path to create the file on disk

**Test results:** 939 tests pass (174 doc-specific). 0 regressions.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Round 3 fixes confirmed: missing OpenAPI handled, integrations auto-linked.
- All 174 doc tests pass.

Blocking issues:

1. **[P2] override.type not applied when merging existing integrations** (`src/qaagent/doc/generator.py:79-87`): The merge branch updates `description`, `env_vars`, `connected_features`, and `source`, but never applies `override.type`. Manual type overrides are silently dropped.

2. **[P2] React Flow diagrams don't refresh when props change** (`src/qaagent/dashboard/frontend/src/components/Doc/IntegrationMapDiagram.tsx:50`, `RouteGraphDiagram.tsx:44`): `useNodesState(initialNodes)` only consumes the initial value. When the parent re-renders with new data (e.g., after regeneration), the diagrams show stale nodes/edges. `FeatureMapDiagram` has the same issue.

3. **[P2] package-lock.json not updated for @xyflow/react** (`src/qaagent/dashboard/frontend/package-lock.json`): `@xyflow/react` was added to `package.json` but `npm install` was never run, so the lockfile is stale.

---

## Round 5

### Lead
**Action:** SUBMIT_FOR_REVIEW

All 3 blocking issues from Round 4 are resolved.

**1. [P2] Apply override.type when merging existing integrations** (`src/qaagent/doc/generator.py:83-87`)
- Added type override logic in the existing-integration merge branch
- When `override.type` is set and not "unknown", it updates `existing.type` via `IntegrationType(override.type)`

**2. [P2] React Flow diagrams refresh on prop changes** (all 3 diagram components)
- Added `useEffect` hooks to sync `flowNodes`/`flowEdges` with `initialNodes`/`initialEdges`
- Applied to `FeatureMapDiagram.tsx`, `IntegrationMapDiagram.tsx`, and `RouteGraphDiagram.tsx`
- Pattern: destructure setters from `useNodesState`/`useEdgesState`, add `useEffect(() => { setFlowNodes(initialNodes); }, [initialNodes, setFlowNodes])`

**3. [P2] package-lock.json updated** (`src/qaagent/dashboard/frontend/package-lock.json`)
- Ran `npm install` in the frontend directory
- Lockfile now includes `@xyflow/react` and its 16 dependencies

**Test results:** 939 tests pass (174 doc-specific). 0 regressions.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Round 5 fixes confirmed: override.type applied, React Flow diagrams refresh, lockfile updated.
- All 174 doc tests pass. Frontend builds cleanly (`tsc -b && vite build`).

Blocking issues:

1. **[P2] Generalize version-prefix skipping** (`src/qaagent/doc/feature_grouper.py:48`): `_extract_prefix` only skips `v1`-`v3`, so `/api/v10/users` groups under `v10` instead of `users`. Same issue in `graph_builder.py` — false shared-prefix edges for v4+ APIs.

2. **[P3] Content hash is order-dependent** (`src/qaagent/doc/generator.py:31-32`): `_compute_content_hash` hashes routes and integrations in discovery order. Different traversal order produces different hashes, causing unnecessary staleness churn.

---

## Round 6

### Lead
**Action:** SUBMIT_FOR_REVIEW

All 3 issues (2 blocking, 1 from graph_builder) from Round 5 are resolved.

**1. [P2] Generalize version-prefix skipping** (`feature_grouper.py:48`, `graph_builder.py:68,153`)
- Replaced fixed `{"api", "v1", "v2", "v3"}` sets with `re.fullmatch(r"v\d+", seg)` regex
- Now correctly skips any `vN` segment (v1, v4, v10, v100, etc.)
- Applied in all 3 locations: `_extract_prefix()`, `build_feature_map()`, `build_route_graph()`
- 3 new tests: `test_high_version_number`, `test_v4_prefix`, `test_no_false_edges_for_high_version_numbers`

**2. [P3] Content hash is now order-independent** (`src/qaagent/doc/generator.py:31-32`)
- Sort route tuples and integration IDs before hashing
- Same content in any discovery order produces the same hash
- 1 new test: `test_hash_order_independent`

**Test results:** 178 doc-specific tests pass. 0 regressions.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Round 6 fixes confirmed: vN skipping generalized in feature_grouper and graph_builder feature_map/route_graph, content hash order-independent.
- All 178 doc tests pass. Frontend builds cleanly.

Blocking issues:

1. **[P2] `_path_matches_prefix` still uses fixed v1-v3 set** (`src/qaagent/doc/graph_builder.py:208`): The route_count calculation uses `_path_matches_prefix` which still has `{"api", "v1", "v2", "v3"}`. Routes under `/api/v10/users` get `route_count: 0` because `v10` is not filtered. Same issue in `cuj_discoverer.py:46`.

2. **[P3] Build-output directories not excluded from JS scanning** (`src/qaagent/doc/integration_detector.py:129`): `dist/`, `build/`, `.next/`, `out/` are not in `skip_dirs`, so bundled JS artifacts report false-positive integrations.

---

## Round 7

### Lead
**Action:** SUBMIT_FOR_REVIEW

Both issues from Round 6 are resolved.

**1. [P2] Generalized vN skipping in _path_matches_prefix and cuj_discoverer** (`graph_builder.py:208`, `cuj_discoverer.py:46`)
- Replaced fixed `{"api", "v1", "v2", "v3"}` with `re.fullmatch(r"v\d+")` in both locations
- Route counts and CUJ keyword extraction now handle v4+ APIs correctly

**2. [P3] Build-output directories excluded from scanning** (`integration_detector.py:129`)
- Added `dist`, `build`, `.next`, `out` to `skip_dirs`
- Prevents false-positive integrations from bundled JS artifacts
- 1 new test: `test_skips_dist_directory`

**Test results:** 179 doc-specific tests pass. 0 regressions.

### Reviewer
**Action:** REQUEST_CHANGES

Verdict: REQUEST_CHANGES

What I validated:
- Round 7 fixes confirmed: vN regex applied everywhere, dist/build dirs excluded.
- All 179 doc tests pass. Frontend builds cleanly.

Blocking issues:

1. **[P2] Skip-dir matching uses absolute path parts** (`integration_detector.py:136`): `skip_dirs.intersection(py_file.parts)` checks against full absolute path, so a repo under `/tmp/build/myrepo` matches "build" and skips all files. Should use `relative_to(source_dir).parts`.

2. **[P3] Rich markup eats integration type brackets** (`doc_cmd.py:103`): `[{i.type.value}]` is parsed as Rich markup, hiding the type label.

---

## Round 8

### Lead
**Action:** SUBMIT_FOR_REVIEW

Both issues from Round 7 are resolved.

**1. [P2] Relative path skip-dir matching** (`integration_detector.py:136,144`)
- Changed `py_file.parts` → `py_file.relative_to(source_dir).parts`
- Same for JS scanning
- Parent directory names no longer suppress scanning

**2. [P3] Escape Rich brackets in doc show** (`doc_cmd.py:103`)
- Changed `[{i.type.value}]` → `\\[{i.type.value}]` to escape Rich markup
- Type label now renders as literal text

**Test results:** 179 doc-specific tests pass. 0 regressions.

### Reviewer
_awaiting response_

---

<!-- CYCLE_STATUS (single source of truth - do not duplicate above) -->
READY_FOR: reviewer
ROUND: 8
STATE: in-progress
<!-- /CYCLE_STATUS -->

