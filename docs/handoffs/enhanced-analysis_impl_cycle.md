# Implementation Cycle: Enhanced Analysis

## Round 1

### Changes Made
All three milestones (4A, 4B, 4C) implemented in a single round.

#### Milestone 4A: Python Framework Route Discovery
- Created `FrameworkParser` ABC with `RouteParam` internal model and `_normalize_route()` method
- Implemented `FastAPIParser` (AST-based, handles `include_router()` prefix chains, `Depends()` auth detection)
- Implemented `FlaskParser` (AST-based, Blueprint prefix composition, Flask converter type mapping)
- Implemented `DjangoParser` (URL pattern regex + DRF ViewSet/router AST parsing)
- Updated `route_discovery.py` with `discover_from_source()` function and auto-detection in `discover_routes()`
- Added `get_framework_parser()` factory to `discovery/__init__.py` and `RepoValidator`
- 45 discovery tests including cross-module regression through risk assessment, test generation, and OpenAPI generation

#### Milestone 4B: Pluggable Risk Rule Engine
- Created `RiskRule` ABC with two-tier evaluation (`evaluate()` per-route, `evaluate_all()` aggregate)
- Created `RiskRuleRegistry` with `run_all()` and disable support
- Implemented 16 rules: 8 security (SEC-001–008), 4 performance (PERF-001–004), 4 reliability (REL-001–004)
- REL-003 (InconsistentNaming) and REL-004 (MissingHealthCheck) are aggregate rules overriding `evaluate_all()`
- Replaced hardcoded rules in `risk_assessment.py` with `default_registry().run_all()`
- Added `disabled_rules` parameter to `assess_risks()`
- 46 rule engine tests

#### Milestone 4C: CI/CD Template Generation
- Created `CICDGenerator` with Jinja2 templates for GitHub Actions and GitLab CI
- All generated pipelines include bootstrap steps (`config init` + `use`) for clean CI runners
- Added `generate ci` CLI command with `--platform`, `--project-name`, `--framework` flags
- Updated CLI snapshot
- 16 CI/CD generator tests, including YAML validity checks

### Test Results
- 127 new tests added
- 0 new regressions (4 pre-existing failures unchanged)
- All milestones verified against success criteria

### Files
See `docs/phases/enhanced-analysis_impl.md` for complete file list.

## Round 2

### Changes Made (addressing reviewer feedback from round 1)

#### Issue 1 [HIGH]: Generated CI templates use invalid CLI invocations
- Fixed `analyze strategy --routes` → `--routes-file` in both GitHub Actions and GitLab CI templates
- Fixed `report generate --format html` → `report --fmt html` in both templates

#### Issue 2 [HIGH]: Test generation steps don't pass discovered routes
- Added `--routes-file routes.json` to all `generate unit-tests`, `generate behave`, and `generate e2e` steps in both templates

#### Issue 3 [HIGH]: GitLab template active-target state not persisted across jobs
- Replaced single `setup` stage with a YAML anchor `.bootstrap: &bootstrap` that each job references via `*bootstrap`
- Each job that needs profile state now runs the full bootstrap (install + config init + use)
- Removed separate `setup` stage; stages are now `analyze → generate → test → report`
- E2E generate step also bootstraps; run-only jobs (run-unit-tests, run-behave-tests, run-e2e-tests, qa-report) that don't call qaagent profile commands just install qaagent directly

#### Issue 4 [MEDIUM]: Plan says `--source-dir` but implementation uses `--source`
- Added `--source-dir` as a CLI alias for `--source` on the `analyze routes` command

#### Issue 5 [MEDIUM]: Next.js parser not migrated to FrameworkParser
- Refactored `NextJsRouteDiscoverer` to extend `FrameworkParser`
- Now uses `_normalize_route()` for consistent `Route.params` shape (`Dict[str, List[dict]]`)
- Added `parse()` and `find_route_files()` abstract method implementations
- Registered `"nextjs"` in `get_framework_parser()` factory
- Updated 4 tests to match new API (`_extract_tag`, `_extract_path_params`, `find_route_files`)

#### Issue 6 [MEDIUM]: Rule disabling not wired through CLI
- Added `_resolve_disabled_rules(active_profile)` helper to `generate_cmd.py`
- Threaded `disabled_rules` from `active_profile.risk_assessment.disable_rules` into all 5 `assess_risks()` call sites (1 in `analyze_cmd.py`, 4 in `generate_cmd.py`)

### Test Results
- 0 new regressions (same 4 pre-existing failures unchanged)
- All 127+ Phase 4 tests pass
- Next.js parser tests updated and passing

### Reviewer (Round 2)
**Action:** REQUEST_CHANGES — 1 remaining MEDIUM issue.

1. **[MEDIUM]** `analyze strategy --routes-file` still bypasses profile `disable_rules` because `active_profile` is only loaded in the no-input fallback path.

## Round 3

### Changes Made

#### Issue 1 [MEDIUM]: `analyze strategy --routes-file` ignores profile `disable_rules`
- Moved `load_active_profile()` call to the top of `analyze_strategy()` (best-effort, before route resolution branches)
- `active_profile` is now available for `disabled_rules` regardless of whether routes come from `--routes-file`, `--openapi`, or active target
- Also fixed error message to reference `--routes-file` (was `--routes`)

### Test Results
- 0 new regressions (same 4 pre-existing failures unchanged)
- All Phase 4 tests pass
